# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgencyConversation(models.Model):
    """Conversation thread between admin and agency"""
    _name = 'agency.conversation'
    _description = 'Agency Conversation'
    _order = 'last_message_date desc'

    name = fields.Char(
        string='Subject',
        required=True
    )
    agency_id = fields.Many2one(
        'travel.agency',
        string='Agency',
        required=True,
        ondelete='cascade'
    )

    # Messages
    message_ids = fields.One2many(
        'agency.message',
        'conversation_id',
        string='Messages'
    )
    message_count = fields.Integer(
        string='Message Count',
        compute='_compute_message_stats'
    )
    unread_admin_count = fields.Integer(
        string='Unread by Admin',
        compute='_compute_message_stats'
    )
    unread_agency_count = fields.Integer(
        string='Unread by Agency',
        compute='_compute_message_stats'
    )

    # Status
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='open')

    # Last activity
    last_message_date = fields.Datetime(
        string='Last Message',
        compute='_compute_last_message',
        store=True
    )
    last_message_preview = fields.Text(
        string='Last Message Preview',
        compute='_compute_last_message',
        store=True
    )

    # Participants
    admin_user_id = fields.Many2one(
        'res.users',
        string='Admin User',
        help='Admin user handling this conversation'
    )
    agency_user_id = fields.Many2one(
        'agency.user',
        string='Agency User',
        help='Agency user who started the conversation'
    )

    # Timestamps
    create_date = fields.Datetime(string='Created', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('message_ids', 'message_ids.is_read_by_admin', 'message_ids.is_read_by_agency')
    def _compute_message_stats(self):
        for conv in self:
            conv.message_count = len(conv.message_ids)
            conv.unread_admin_count = len(conv.message_ids.filtered(
                lambda m: m.sender_type == 'agency' and not m.is_read_by_admin
            ))
            conv.unread_agency_count = len(conv.message_ids.filtered(
                lambda m: m.sender_type == 'admin' and not m.is_read_by_agency
            ))

    @api.depends('message_ids', 'message_ids.create_date')
    def _compute_last_message(self):
        for conv in self:
            last_msg = conv.message_ids.sorted('create_date', reverse=True)[:1]
            if last_msg:
                conv.last_message_date = last_msg.create_date
                # Strip HTML and truncate
                import re
                body = re.sub('<[^<]+?>', '', last_msg.body or '')
                conv.last_message_preview = body[:100] + '...' if len(body) > 100 else body
            else:
                conv.last_message_date = conv.create_date
                conv.last_message_preview = ''

    def action_close(self):
        """Close the conversation"""
        self.write({'state': 'closed'})

    def action_reopen(self):
        """Reopen the conversation"""
        self.write({'state': 'open'})

    def action_view_messages(self):
        """View messages in conversation"""
        self.ensure_one()
        # Mark all unread messages from agency as read by admin
        self.mark_messages_as_read_by_admin()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'agency.message',
            'view_mode': 'tree,form',
            'domain': [('conversation_id', '=', self.id)],
            'context': {'default_conversation_id': self.id},
        }

    def mark_messages_as_read_by_admin(self):
        """Mark all agency messages as read by admin"""
        for conv in self:
            unread_messages = conv.message_ids.filtered(
                lambda m: m.sender_type == 'agency' and not m.is_read_by_admin
            )
            unread_messages.mark_as_read_admin()

    def read(self, fields=None, load='_classic_read'):
        """Override read to mark messages as read when conversation is viewed"""
        result = super().read(fields, load)
        # Mark messages as read when admin views the conversation
        if self.env.user.has_group('eth_agency_core.group_agency_user'):
            self.mark_messages_as_read_by_admin()
        return result


class AgencyMessage(models.Model):
    """Individual message in a conversation"""
    _name = 'agency.message'
    _description = 'Agency Message'
    _order = 'create_date asc'

    conversation_id = fields.Many2one(
        'agency.conversation',
        string='Conversation',
        required=True,
        ondelete='cascade'
    )
    agency_id = fields.Many2one(
        related='conversation_id.agency_id',
        string='Agency',
        store=True
    )

    # Message content
    body = fields.Html(
        string='Message',
        required=True
    )

    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'agency_message_attachment_rel',
        'message_id',
        'attachment_id',
        string='Attachments'
    )

    # Sender
    sender_type = fields.Selection([
        ('admin', 'Admin'),
        ('agency', 'Agency'),
    ], string='Sender Type', required=True)

    sender_admin_id = fields.Many2one(
        'res.users',
        string='Admin Sender'
    )
    sender_agency_user_id = fields.Many2one(
        'agency.user',
        string='Agency Sender'
    )

    # Read status
    is_read_by_admin = fields.Boolean(
        string='Read by Admin',
        default=False
    )
    is_read_by_agency = fields.Boolean(
        string='Read by Agency',
        default=False
    )
    read_by_admin_date = fields.Datetime(string='Read by Admin Date')
    read_by_agency_date = fields.Datetime(string='Read by Agency Date')

    # Timestamps
    create_date = fields.Datetime(string='Sent', readonly=True)

    def mark_as_read_admin(self):
        """Mark message as read by admin"""
        self.filtered(lambda m: not m.is_read_by_admin).write({
            'is_read_by_admin': True,
            'read_by_admin_date': fields.Datetime.now()
        })

    def mark_as_read_agency(self):
        """Mark message as read by agency"""
        self.filtered(lambda m: not m.is_read_by_agency).write({
            'is_read_by_agency': True,
            'read_by_agency_date': fields.Datetime.now()
        })

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-set read status based on sender"""
        for vals in vals_list:
            if vals.get('sender_type') == 'admin':
                vals['is_read_by_admin'] = True
            elif vals.get('sender_type') == 'agency':
                vals['is_read_by_agency'] = True
        return super().create(vals_list)

    def action_send_admin_reply(self):
        """Send reply from admin"""
        self.ensure_one()
        self.write({
            'sender_type': 'admin',
            'sender_admin_id': self.env.user.id,
            'is_read_by_admin': True,
        })
        return {'type': 'ir.actions.act_window_close'}
