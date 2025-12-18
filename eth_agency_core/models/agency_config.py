# -*- coding: utf-8 -*-
from odoo import fields, models, api


class AgencyConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    # Signup Form Visibility Settings
    agency_show_membership_purposes = fields.Boolean(
        string='Show Membership Purposes on Signup',
        config_parameter='eth_agency_core.show_membership_purposes',
        default=True,
        help='Show/Hide membership purposes section in signup form'
    )


class AgencyConfigHelper(models.AbstractModel):
    """Helper model to access agency configuration from other models and templates"""
    _name = 'agency.config.helper'
    _description = 'Agency Configuration Helper'

    @api.model
    def get_agency_config(self):
        """Get current agency configuration as a dictionary"""
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'show_membership_purposes': ICP.get_param(
                'eth_agency_core.show_membership_purposes', 'True'
            ) == 'True',
        }

    @api.model
    def should_show_membership_purposes(self):
        """Check if membership purposes should be shown"""
        config = self.get_agency_config()
        return config['show_membership_purposes']
