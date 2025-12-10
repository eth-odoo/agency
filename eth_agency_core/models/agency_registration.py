# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import secrets
import string

_logger = logging.getLogger(__name__)


class AgencyRegistration(models.Model):
    _name = 'agency.registration'
    _description = 'Agency Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Registration Name',
        required=True,
        default=lambda self: _('New Registration'),
        tracking=True
    )

    # Agency Information
    agency_name = fields.Char(string='Agency Name', required=True, tracking=True)
    authorized_first_name = fields.Char(string='Authorized First Name', required=True, tracking=True)
    authorized_last_name = fields.Char(string='Authorized Last Name', required=True, tracking=True)
    authorized_email = fields.Char(string='Authorized Email', required=True, tracking=True)
    phone_number = fields.Char(string='Phone Number', tracking=True)

    # Agency Location
    country_id = fields.Many2one('res.country', string='Agency Country', required=True, tracking=True)
    city_id = fields.Many2one('res.country.state', string='Agency City', required=True, tracking=True)
    city = fields.Char(string='City Name', compute='_compute_city_name', store=True, readonly=True)
    address = fields.Text(string='Agency Address', required=True, tracking=True)

    # User Location (separate from agency)
    user_country_id = fields.Many2one('res.country', string='User Country', tracking=True)
    user_city_id = fields.Many2one('res.country.state', string='User City', tracking=True)
    user_address = fields.Text(string='User Address', tracking=True)

    # Language and Preferences
    preferred_language = fields.Selection([
        ('tr', 'Turkish'),
        ('en', 'English'),
        ('de', 'German'),
        ('fr', 'French'),
        ('es', 'Spanish'),
        ('it', 'Italian'),
        ('ru', 'Russian'),
        ('ar', 'Arabic'),
    ], string='Preferred Language', required=True, default='tr', tracking=True)

    # Membership Purposes
    membership_purpose_ids = fields.Many2many(
        'agency.membership.purpose',
        'agency_registration_purpose_rel',
        'registration_id',
        'purpose_id',
        string='Membership Purposes',
        tracking=True
    )

    # Document Upload
    confirmation_file = fields.Binary(string='Confirmation File')
    confirmation_file_name = fields.Char(string='Confirmation File Name')

    # Business Information
    business_registration_number = fields.Char(string='Business Registration Number', tracking=True)
    tax_office = fields.Char(string='Tax Office', tracking=True)
    iata_code = fields.Char(string='IATA Code', tracking=True)
    has_iata_accreditation = fields.Boolean(string='Has IATA Accreditation', tracking=True)

    # Status and Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('document_pending', 'Document Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    # Terms and Conditions
    terms_accepted = fields.Boolean(string='Terms Accepted')
    terms_acceptance_date = fields.Datetime(string='Terms Acceptance Date')

    # CRM Integration
    opportunity_id = fields.Many2one('crm.lead', string='CRM Opportunity')

    # Created Records
    partner_id = fields.Many2one('res.partner', string='Created Partner')
    agency_id = fields.Many2one('agency.agency', string='Created Agency')
    agency_user_id = fields.Many2one('agency.user', string='Created Agency User')
    user_id = fields.Many2one('res.users', string='Created User')

    # Approval Information
    approved_by = fields.Many2one('res.users', string='Approved By', tracking=True)
    approved_date = fields.Datetime(string='Approved Date', tracking=True)
    rejected_by = fields.Many2one('res.users', string='Rejected By', tracking=True)
    rejected_date = fields.Datetime(string='Rejected Date', tracking=True)
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)

    notes = fields.Text(string='Internal Notes')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, tracking=True
    )

    @api.depends('city_id')
    def _compute_city_name(self):
        for record in self:
            record.city = record.city_id.name if record.city_id else ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New Registration')) == _('New Registration'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'agency.registration'
                ) or _('New Registration')
            if vals.get('terms_accepted'):
                vals['terms_acceptance_date'] = fields.Datetime.now()
        return super(AgencyRegistration, self).create(vals_list)

    def action_submit(self):
        """Submit registration for review"""
        if not self.terms_accepted:
            raise ValidationError(_('Please accept the terms and conditions.'))
        self.state = 'submitted'
        self.create_crm_opportunity()
        self._send_confirmation_email()
        self.message_post(body=_('Registration submitted for review.'))
        return True

    def action_start_review(self):
        """Start review process"""
        self.state = 'under_review'
        self.message_post(body=_('Review process started.'))
        return True

    def action_request_documents(self):
        """Request additional documents"""
        self.state = 'document_pending'
        self.message_post(body=_('Additional documents requested.'))
        return True

    def action_approve(self):
        """Approve registration and create agency"""
        self.state = 'approved'
        self.approved_by = self.env.user
        self.approved_date = fields.Datetime.now()

        partner = self._create_partner()
        agency = self._create_agency(partner)
        self._create_master_user(agency)

        if self.opportunity_id:
            self.opportunity_id.action_set_won()

        self._send_approval_email()
        self.message_post(body=_('Registration approved. Agency created.'))
        return True

    def action_reject(self):
        """Open reject wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Registration'),
            'res_model': 'agency.registration.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_registration_id': self.id}
        }

    def _create_partner(self):
        """Create partner from registration"""
        if self.partner_id:
            return self.partner_id

        agency_code = self.env['ir.sequence'].next_by_code('agency.code') or 'AGN00001'

        partner = self.env['res.partner'].create({
            'name': self.agency_name,
            'is_company': True,
            'is_agency': True,
            'agency_code': agency_code,
            'email': self.authorized_email,
            'phone': self.phone_number,
            'street': self.address,
            'city': self.city,
            'country_id': self.country_id.id,
            'company_id': self.company_id.id,
        })

        self.partner_id = partner.id
        return partner

    def _create_agency(self, partner):
        """Create agency record"""
        if self.agency_id:
            return self.agency_id

        agency = self.env['agency.agency'].create({
            'name': self.agency_name,
            'partner_id': partner.id,
            'code': partner.agency_code or self.env['ir.sequence'].next_by_code('agency.agency'),
            'state': 'active',
            'contract_start_date': fields.Date.today(),
            'membership_purpose_ids': [(6, 0, self.membership_purpose_ids.ids)],
            'preferred_language': self.preferred_language,
            'registration_id': self.id,
            'company_id': self.company_id.id,
        })

        self.agency_id = agency.id
        return agency

    def _create_master_user(self, agency):
        """Create master user for agency"""
        if self.agency_user_id:
            return self.agency_user_id

        password = self._generate_password()

        master_user = agency.create_master_user({
            'name': f'{self.authorized_first_name} {self.authorized_last_name}',
            'email': self.authorized_email,
            'phone': self.phone_number,
            'password': password,
            'country_id': self.user_country_id.id if self.user_country_id else False,
            'city_id': self.user_city_id.id if self.user_city_id else False,
            'address': self.user_address or False,
        })

        self.agency_user_id = master_user.id
        self._send_welcome_email(master_user, password)
        return master_user

    def _generate_password(self, length=12):
        """Generate secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def create_crm_opportunity(self):
        """Create CRM opportunity"""
        if self.opportunity_id:
            return self.opportunity_id

        team = self.env['crm.team'].search([], limit=1)
        purposes = ', '.join(self.membership_purpose_ids.mapped('name'))

        opportunity = self.env['crm.lead'].create({
            'name': f'Agency Registration: {self.agency_name}',
            'partner_name': self.agency_name,
            'contact_name': f'{self.authorized_first_name} {self.authorized_last_name}',
            'email_from': self.authorized_email,
            'phone': self.phone_number,
            'street': self.address,
            'city': self.city,
            'country_id': self.country_id.id,
            'team_id': team.id if team else False,
            'company_id': self.company_id.id,
            'description': f'Membership Purposes: {purposes}',
        })

        self.opportunity_id = opportunity.id
        return opportunity

    def _send_confirmation_email(self):
        """Send confirmation email"""
        template = self.env.ref(
            'eth_agency_core.email_template_registration_confirmation',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_approval_email(self):
        """Send approval email"""
        template = self.env.ref(
            'eth_agency_core.email_template_registration_approved',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_welcome_email(self, user, password):
        """Send welcome email with credentials"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        login_url = f"{base_url}/agency/login"

        body = f"""
        <h2>Welcome to the Agency Portal!</h2>
        <p>Dear {user.name},</p>
        <p>Your agency <strong>{self.agency_name}</strong> has been approved.</p>
        <p><strong>Login Credentials:</strong></p>
        <p>Email: {user.email}<br/>Password: {password}</p>
        <p><a href="{login_url}">Login to Agency Portal</a></p>
        <p>Please change your password after first login.</p>
        """

        mail = self.env['mail.mail'].create({
            'subject': f'Welcome to {self.agency_name} - Agency Portal',
            'body_html': body,
            'email_to': user.email,
            'email_from': self.env.company.email,
            'auto_delete': True,
        })
        mail.send()
