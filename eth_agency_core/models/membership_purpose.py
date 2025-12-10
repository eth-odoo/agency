# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AgencyMembershipPurpose(models.Model):
    _name = 'agency.membership.purpose'
    _description = 'Agency Membership Purpose'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description', translate=True)
    icon = fields.Char(string='Icon', help='Icon class for display (e.g., fa-shopping-cart)')
    color = fields.Integer(string='Color Index', default=0)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Purpose code must be unique!')
    ]
