# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Agency(models.Model):
    _name = 'travel.agency'
    _description = 'Agency'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Agency Name',
        required=True,
        tracking=True
    )

    # Partner Link
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        domain=[('is_agency', '=', True)],
        tracking=True
    )

    # Basic Information
    code = fields.Char(
        string='Agency Code',
        required=True,
        tracking=True
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ], string='Status', default='draft', tracking=True)

    # Contract Information
    contract_start_date = fields.Date(
        string='Contract Start Date',
        tracking=True
    )
    contract_end_date = fields.Date(
        string='Contract End Date',
        tracking=True
    )

    # Agency Group & Commission Settings
    agency_group_id = fields.Many2one(
        'agency.group',
        string='Agency Group',
        tracking=True,
        help='Agency group determines commission type and percentage'
    )
    commission_type = fields.Selection(
        related='agency_group_id.commission_type',
        string='Commission Type',
        store=True,
        readonly=True
    )
    commission_percentage = fields.Float(
        related='agency_group_id.commission_percentage',
        string='Commission Percentage (%)',
        store=True,
        readonly=True
    )
    # Keep for backward compatibility
    default_commission_rate = fields.Float(
        string='Default Commission Rate (%)',
        default=10.0,
        tracking=True
    )

    # Membership Purposes
    membership_purpose_ids = fields.Many2many(
        'agency.membership.purpose',
        'agency_purpose_rel',
        'agency_id',
        'purpose_id',
        string='Membership Purposes',
        tracking=True
    )

    preferred_language = fields.Selection([
        ('tr', 'Turkish'),
        ('en', 'English'),
        ('de', 'German'),
        ('fr', 'French'),
        ('es', 'Spanish'),
        ('it', 'Italian'),
        ('ru', 'Russian'),
        ('ar', 'Arabic'),
    ], string='Preferred Language', tracking=True)

    # Default language for portal
    default_language = fields.Selection([
        ('tr_TR', 'Turkish'),
        ('en_US', 'English'),
    ], string='Default Portal Language', default='en_US')

    registration_id = fields.Many2one(
        'agency.registration',
        string='Source Registration',
        readonly=True,
        help='Original registration that created this agency'
    )

    # Agency Users
    agency_user_ids = fields.One2many(
        'agency.user',
        'agency_id',
        string='Agency Users'
    )
    master_user_id = fields.Many2one(
        'agency.user',
        string='Master User',
        domain="[('agency_id', '=', id), ('is_master', '=', True)]"
    )
    user_count = fields.Integer(
        string='User Count',
        compute='_compute_user_count',
        store=True
    )

    # Statistics
    total_bookings = fields.Integer(
        string='Total Bookings',
        compute='_compute_statistics'
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_statistics'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # Communication
    conversation_ids = fields.One2many(
        'agency.conversation',
        'agency_id',
        string='Conversations'
    )
    conversation_count = fields.Integer(
        string='Conversations',
        compute='_compute_communication_stats'
    )
    unread_message_count = fields.Integer(
        string='Unread Messages',
        compute='_compute_communication_stats'
    )
    announcement_read_ids = fields.One2many(
        'agency.announcement.read',
        'agency_id',
        string='Read Announcements'
    )
    announcement_count = fields.Integer(
        string='Announcements Sent',
        compute='_compute_communication_stats'
    )

    # Update Requests
    update_request_ids = fields.One2many(
        'agency.update.request',
        'agency_id',
        string='Update Requests'
    )
    pending_request_count = fields.Integer(
        string='Pending Requests',
        compute='_compute_request_stats'
    )

    # Related Fields from Partner
    email = fields.Char(
        related='partner_id.email',
        string='Email',
        readonly=False,
        store=True
    )
    phone = fields.Char(
        related='partner_id.phone',
        string='Phone',
        readonly=False,
        store=True
    )
    website = fields.Char(
        related='partner_id.website',
        string='Website',
        readonly=False,
        store=True
    )
    country_id = fields.Many2one(
        related='partner_id.country_id',
        string='Country',
        readonly=True
    )
    city = fields.Char(
        related='partner_id.city',
        string='City',
        readonly=True
    )

    # Multi-company Support
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=True
    )

    @api.depends('agency_user_ids.active')
    def _compute_user_count(self):
        """Compute number of agency users"""
        for agency in self:
            agency.user_count = len(agency.agency_user_ids.filtered('active'))

    def _compute_statistics(self):
        """Compute agency statistics - override in extensions"""
        for agency in self:
            agency.total_bookings = 0
            agency.total_revenue = 0.0

    def _compute_communication_stats(self):
        """Compute communication statistics"""
        Announcement = self.env['agency.announcement'].sudo()
        for agency in self:
            # Conversation count
            agency.conversation_count = len(agency.conversation_ids)

            # Unread message count (messages from agency that admin hasn't read)
            unread = 0
            for conv in agency.conversation_ids:
                unread += conv.unread_admin_count
            agency.unread_message_count = unread

            # Count announcements targeted at this agency
            all_announcements = Announcement.search([('state', '=', 'published')])
            count = 0
            for ann in all_announcements:
                if ann.target_type == 'all':
                    count += 1
                elif ann.target_type == 'selected' and agency in ann.agency_ids:
                    count += 1
                elif ann.target_type == 'by_group' and agency.agency_group_id in ann.agency_group_ids:
                    count += 1
                elif ann.target_type == 'by_country' and agency.country_id in ann.country_ids:
                    count += 1
                elif ann.target_type == 'by_language' and agency.preferred_language == ann.target_languages:
                    count += 1
            agency.announcement_count = count

    def _compute_request_stats(self):
        """Compute update request statistics"""
        for agency in self:
            agency.pending_request_count = len(agency.update_request_ids.filtered(
                lambda r: r.state == 'pending'
            ))

    def action_view_update_requests(self):
        """View update requests for this agency"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Requests'),
            'res_model': 'agency.update.request',
            'view_mode': 'list,form',
            'domain': [('agency_id', '=', self.id)],
            'context': {'default_agency_id': self.id},
        }

    def action_activate(self):
        """Activate agency"""
        self.state = 'active'
        return True

    def action_suspend(self):
        """Suspend agency"""
        self.state = 'suspended'
        return True

    def action_terminate(self):
        """Terminate agency"""
        self.state = 'terminated'
        return True

    def action_view_partner(self):
        """View partner record"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Agency Partner'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }

    def action_view_users(self):
        """View agency users"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Agency Users'),
            'res_model': 'agency.user',
            'view_mode': 'list,form',
            'domain': [('agency_id', '=', self.id)],
            'context': {'default_agency_id': self.id},
            'target': 'current',
        }

    def action_view_conversations(self):
        """View agency conversations"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Conversations'),
            'res_model': 'agency.conversation',
            'view_mode': 'list,form',
            'domain': [('agency_id', '=', self.id)],
            'context': {'default_agency_id': self.id},
            'target': 'current',
        }

    def action_view_registration(self):
        """View original registration"""
        if self.registration_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Original Registration'),
                'res_model': 'agency.registration',
                'view_mode': 'form',
                'res_id': self.registration_id.id,
                'target': 'current',
            }
        return False

    def create_master_user(self, user_data):
        """Create master user after agency registration"""
        if self.master_user_id:
            raise ValidationError(_('Agency already has a master user!'))

        # Validate required fields
        required_fields = ['name', 'email', 'password']
        for field in required_fields:
            if not user_data.get(field):
                raise ValidationError(_('%s is required for master user!') % field.title())

        # Prepare master user values
        master_user_vals = {
            'name': user_data['name'],
            'email': user_data['email'].lower().strip(),
            'phone': user_data.get('phone', ''),
            'agency_id': self.id,
            'is_master': True,
            'can_create_users': True,
            'can_manage_bookings': True,
            'can_view_reports': True,
            'can_manage_agency': True,
        }

        # Add location fields if provided
        if user_data.get('country_id'):
            master_user_vals['country_id'] = user_data['country_id']
        if user_data.get('city_id'):
            master_user_vals['city_id'] = user_data['city_id']
        if user_data.get('address'):
            master_user_vals['address'] = user_data['address']

        # Create master user
        master_user = self.env['agency.user'].create(master_user_vals)

        # Set password
        master_user.set_password(user_data['password'])

        # Update agency master user
        self.master_user_id = master_user.id

        return master_user

    def get_active_users(self):
        """Get active agency users"""
        return self.agency_user_ids.filtered('active')

    def get_user_by_email(self, email):
        """Get user by email"""
        return self.agency_user_ids.filtered(
            lambda u: u.email == email.lower().strip() and u.active
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-generate code if not provided
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('travel.agency') or 'AGN001'
        return super(Agency, self).create(vals_list)

    @api.constrains('code')
    def _check_code_unique(self):
        for agency in self:
            if agency.code:
                existing = self.search([
                    ('code', '=', agency.code),
                    ('id', '!=', agency.id)
                ])
                if existing:
                    raise ValidationError(
                        _('Agency code must be unique. Code "%s" is already used.') % agency.code
                    )
