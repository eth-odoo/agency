# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    registration_id = fields.Many2one(
        'agency.registration',
        string='Agency Registration',
        help='Related agency registration'
    )

    def action_view_registration(self):
        """View related registration"""
        if self.registration_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Agency Registration',
                'res_model': 'agency.registration',
                'view_mode': 'form',
                'res_id': self.registration_id.id,
                'target': 'current',
            }
        return False
