# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgencyGroup(models.Model):
    _name = 'agency.group'
    _description = 'Agency Group'
    _order = 'sequence, name'

    name = fields.Char(
        string='Group Name',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='Code',
        required=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Commission Settings
    commission_type = fields.Selection([
        ('net', 'Net'),
        ('gross', 'Gross'),
    ], string='Commission Type', required=True, default='gross')

    commission_percentage = fields.Float(
        string='Commission Percentage (%)',
        default=10.0,
        help='Commission percentage for this agency group'
    )

    # Description
    description = fields.Text(
        string='Description',
        translate=True
    )

    # Related Agencies
    agency_ids = fields.One2many(
        'travel.agency',
        'agency_group_id',
        string='Agencies'
    )
    agency_count = fields.Integer(
        string='Agency Count',
        compute='_compute_agency_count'
    )

    # Is Default Group
    is_default = fields.Boolean(
        string='Default Group',
        default=False,
        help='If checked, new agencies will be assigned to this group by default'
    )

    @api.depends('agency_ids')
    def _compute_agency_count(self):
        for group in self:
            group.agency_count = len(group.agency_ids)

    @api.constrains('code')
    def _check_code_unique(self):
        for group in self:
            if group.code:
                existing = self.search([
                    ('code', '=', group.code),
                    ('id', '!=', group.id)
                ])
                if existing:
                    raise ValidationError(
                        _('Group code must be unique. Code "%s" is already used.') % group.code
                    )

    @api.constrains('is_default')
    def _check_single_default(self):
        """Ensure only one group is marked as default"""
        for group in self:
            if group.is_default:
                existing_default = self.search([
                    ('is_default', '=', True),
                    ('id', '!=', group.id)
                ])
                if existing_default:
                    existing_default.write({'is_default': False})

    @api.model
    def get_default_group(self):
        """Get the default agency group"""
        default_group = self.search([('is_default', '=', True)], limit=1)
        if not default_group:
            # Fallback to Platinum Gross if exists
            default_group = self.search([('code', '=', 'platinum_gross')], limit=1)
        return default_group

    @api.onchange('name')
    def _onchange_name(self):
        """Auto-set commission type based on name"""
        if self.name:
            name_lower = self.name.lower()
            if 'net' in name_lower:
                self.commission_type = 'net'
            elif 'gross' in name_lower:
                self.commission_type = 'gross'
