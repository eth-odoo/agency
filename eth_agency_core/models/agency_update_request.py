# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AgencyUpdateRequest(models.Model):
    _name = 'agency.update.request'
    _description = 'Agency Update Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Request Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )

    agency_id = fields.Many2one(
        'travel.agency',
        string='Agency',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    request_type = fields.Selection([
        ('add_membership', 'Add Membership Purpose'),
        ('remove_membership', 'Remove Membership Purpose'),
    ], string='Request Type', required=True, tracking=True)

    # For membership requests
    membership_purpose_ids = fields.Many2many(
        'agency.membership.purpose',
        'agency_update_request_membership_rel',
        'request_id',
        'purpose_id',
        string='Membership Purposes'
    )

    reason = fields.Text(
        string='Reason/Notes',
        help='Explain why this change is needed'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    rejection_reason = fields.Text(
        string='Rejection Reason',
        tracking=True
    )

    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved/Rejected By',
        readonly=True
    )

    approved_date = fields.Datetime(
        string='Approved/Rejected Date',
        readonly=True
    )

    # Computed field for display
    item_names = fields.Char(
        string='Requested Items',
        compute='_compute_item_names',
        store=True
    )

    @api.depends('request_type', 'membership_purpose_ids')
    def _compute_item_names(self):
        for rec in self:
            if rec.request_type in ('add_membership', 'remove_membership') and rec.membership_purpose_ids:
                rec.item_names = ', '.join(rec.membership_purpose_ids.mapped('name'))
            else:
                rec.item_names = ''

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'agency.update.request') or _('New')
        record = super(AgencyUpdateRequest, self).create(vals)

        # Notify admin users about new request
        record._notify_admins_new_request()

        return record

    def _notify_admins_new_request(self):
        """Send notification to admin users about new request"""
        for record in self:
            # Find users in agency admin group
            admin_group = self.env.ref('eth_agency_core.group_agency_admin', raise_if_not_found=False)
            if admin_group:
                admin_users = admin_group.users
                if admin_users:
                    # Create activity for admin users
                    for user in admin_users[:5]:  # Limit to 5 admins
                        record.activity_schedule(
                            'mail.mail_activity_data_todo',
                            user_id=user.id,
                            summary=_('New Agency Update Request'),
                            note=_('Agency %s submitted a new %s request. Please review.') % (
                                record.agency_id.name,
                                dict(record._fields['request_type'].selection).get(record.request_type, record.request_type)
                            )
                        )

            # Post message
            record.message_post(
                body=_('New update request submitted by agency: %s') % record.agency_id.name,
                subject=_('New Update Request: %s') % record.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )

    def action_submit(self):
        """Submit the request for approval"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            record.state = 'pending'

            # Post message in chatter
            record.message_post(
                body=_('Request submitted for approval by %s') % self.env.user.name,
                subject=_('Request Submitted'),
                message_type='notification'
            )

    def action_approve(self):
        """Approve the request and apply changes"""
        for record in self:
            if record.state != 'pending':
                raise UserError(_('Only pending requests can be approved.'))

            # Apply the changes based on request type
            if record.request_type == 'add_membership' and record.membership_purpose_ids:
                record.agency_id.membership_purpose_ids |= record.membership_purpose_ids
                _logger.info(f"Added membership purposes {record.membership_purpose_ids.mapped('name')} to agency {record.agency_id.name}")

            elif record.request_type == 'remove_membership' and record.membership_purpose_ids:
                record.agency_id.membership_purpose_ids -= record.membership_purpose_ids
                _logger.info(f"Removed membership purposes {record.membership_purpose_ids.mapped('name')} from agency {record.agency_id.name}")

            record.write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

            # Mark activities as done
            record.activity_ids.action_done()

            # Post message in chatter
            record.message_post(
                body=_('Request approved by %s and changes applied') % self.env.user.name,
                subject=_('Request Approved'),
                message_type='notification'
            )

    def action_reject(self):
        """Reject the request - open wizard"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending requests can be rejected.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Request'),
            'res_model': 'agency.update.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
            }
        }

    def action_do_reject(self, rejection_reason=None):
        """Actually reject the request"""
        for record in self:
            record.write({
                'state': 'rejected',
                'rejection_reason': rejection_reason,
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

            # Mark activities as done
            record.activity_ids.action_done()

            # Post message
            record.message_post(
                body=_('Request rejected by %s. Reason: %s') % (self.env.user.name, rejection_reason or '-'),
                subject=_('Request Rejected'),
                message_type='notification'
            )

    def action_cancel(self):
        """Cancel the request"""
        for record in self:
            if record.state not in ('draft', 'pending'):
                raise UserError(_('Only draft or pending requests can be cancelled.'))

            record.state = 'cancelled'

            # Mark activities as done
            record.activity_ids.action_done()

            # Post message in chatter
            record.message_post(
                body=_('Request cancelled by %s') % self.env.user.name,
                subject=_('Request Cancelled'),
                message_type='notification'
            )

    def action_reset_to_draft(self):
        """Reset to draft (for admin use)"""
        for record in self:
            if record.state == 'approved':
                raise UserError(_('Approved requests cannot be reset to draft.'))

            record.state = 'draft'
            record.rejection_reason = False

            # Post message in chatter
            record.message_post(
                body=_('Request reset to draft by %s') % self.env.user.name,
                subject=_('Request Reset'),
                message_type='notification'
            )

    @api.model
    def get_pending_requests_count(self):
        """Get count of pending requests for admin notification"""
        return self.search_count([('state', '=', 'pending')])

    @api.depends('request_type', 'membership_purpose_ids')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.name != _('New'):
                name = record.name
                if record.request_type:
                    type_name = dict(self._fields['request_type'].selection).get(record.request_type, record.request_type)
                    name = f"{name} - {type_name}"
                record.display_name = name
            else:
                record.display_name = _('New Request')
