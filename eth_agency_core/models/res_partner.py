# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Agency Fields
    is_agency = fields.Boolean(string='Is Agency', help='Check if this partner is an agency')
    agency_code = fields.Char(string='Agency Code', help='Unique agency code')

    # Approval Status
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('document_pending', 'Document Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)

    # Business Information
    business_registration_number = fields.Char(string='Business Registration Number')
    tax_office = fields.Char(string='Tax Office')
    iata_code = fields.Char(string='IATA Code')
    has_iata_accreditation = fields.Boolean(string='Has IATA Accreditation')

    # Document Upload
    confirmation_file = fields.Binary(string='Confirmation File')
    confirmation_file_name = fields.Char(string='Confirmation File Name')

    # Registration Link
    registration_id = fields.Many2one('agency.registration', string='Registration')

    @api.constrains('agency_code')
    def _check_agency_code_unique(self):
        for partner in self:
            if partner.agency_code:
                existing = self.search([
                    ('agency_code', '=', partner.agency_code),
                    ('id', '!=', partner.id),
                    ('is_agency', '=', True)
                ])
                if existing:
                    raise ValidationError(
                        _('Agency code must be unique. Code "%s" is already used.') % partner.agency_code
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_agency') and not vals.get('agency_code'):
                vals['agency_code'] = self.env['ir.sequence'].next_by_code('agency.code') or 'AGN00001'
        return super(ResPartner, self).create(vals_list)
