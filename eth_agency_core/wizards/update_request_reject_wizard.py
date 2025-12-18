# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AgencyUpdateRequestRejectWizard(models.TransientModel):
    _name = 'agency.update.request.reject.wizard'
    _description = 'Reject Agency Update Request'

    request_id = fields.Many2one(
        'agency.update.request',
        string='Request',
        required=True
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True
    )

    def action_reject(self):
        """Reject the request with reason"""
        self.ensure_one()
        self.request_id.action_do_reject(self.rejection_reason)
        return {'type': 'ir.actions.act_window_close'}
