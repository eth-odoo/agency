# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MessageReplyWizard(models.TransientModel):
    _name = 'agency.message.reply.wizard'
    _description = 'Agency Message Reply Wizard'

    conversation_id = fields.Many2one(
        'agency.conversation',
        string='Conversation',
        required=True
    )
    body = fields.Html(
        string='Message',
        required=True
    )

    def action_send_reply(self):
        """Send reply from admin"""
        self.ensure_one()

        if not self.body:
            raise UserError(_('Please enter a message.'))

        # Create message
        self.env['agency.message'].create({
            'conversation_id': self.conversation_id.id,
            'body': self.body,
            'sender_type': 'admin',
            'sender_admin_id': self.env.user.id,
            'is_read_by_admin': True,
        })

        return {'type': 'ir.actions.act_window_close'}
