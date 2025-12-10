# -*- coding: utf-8 -*-
from odoo import models, fields, _


class AgencyRegistrationRejectWizard(models.TransientModel):
    _name = 'agency.registration.reject.wizard'
    _description = 'Agency Registration Reject Wizard'

    registration_id = fields.Many2one(
        'agency.registration',
        string='Registration',
        required=True,
        readonly=True
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Please provide a detailed reason for rejection'
    )

    def action_reject(self):
        """Reject the registration with reason"""
        self.ensure_one()

        if self.registration_id:
            self.registration_id.write({
                'state': 'rejected',
                'rejected_by': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
                'rejection_reason': self.rejection_reason,
            })

            if self.registration_id.opportunity_id:
                self.registration_id.opportunity_id.action_set_lost()

            self.registration_id.message_post(
                body=_('Registration rejected. Reason: %s') % self.rejection_reason,
            )

        return {'type': 'ir.actions.act_window_close'}
