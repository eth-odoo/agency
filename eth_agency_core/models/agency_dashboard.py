# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class AgencyDashboard(models.TransientModel):
    _name = 'agency.dashboard'
    _description = 'Agency Dashboard'

    # Date filters
    date_from = fields.Date(
        string='From Date',
        default=lambda self: fields.Date.today() - relativedelta(months=1)
    )
    date_to = fields.Date(
        string='To Date',
        default=fields.Date.today
    )

    # ========== REGISTRATION STATS ==========
    total_registrations = fields.Integer(
        string='Total Registrations',
        compute='_compute_registration_stats'
    )
    pending_registrations = fields.Integer(
        string='Pending',
        compute='_compute_registration_stats'
    )
    approved_registrations = fields.Integer(
        string='Approved',
        compute='_compute_registration_stats'
    )
    rejected_registrations = fields.Integer(
        string='Rejected',
        compute='_compute_registration_stats'
    )
    registrations_this_month = fields.Integer(
        string='This Month',
        compute='_compute_registration_stats'
    )

    # ========== AGENCY STATS ==========
    total_agencies = fields.Integer(
        string='Total Agencies',
        compute='_compute_agency_stats'
    )
    active_agencies = fields.Integer(
        string='Active',
        compute='_compute_agency_stats'
    )
    suspended_agencies = fields.Integer(
        string='Suspended',
        compute='_compute_agency_stats'
    )
    terminated_agencies = fields.Integer(
        string='Terminated',
        compute='_compute_agency_stats'
    )

    # ========== MESSAGE STATS ==========
    total_conversations = fields.Integer(
        string='Total Conversations',
        compute='_compute_message_stats'
    )
    open_conversations = fields.Integer(
        string='Open',
        compute='_compute_message_stats'
    )
    total_messages = fields.Integer(
        string='Total Messages',
        compute='_compute_message_stats'
    )
    unread_messages = fields.Integer(
        string='Unread by Admin',
        compute='_compute_message_stats'
    )
    messages_this_month = fields.Integer(
        string='Messages This Month',
        compute='_compute_message_stats'
    )

    # ========== ANNOUNCEMENT STATS ==========
    total_announcements = fields.Integer(
        string='Total Announcements',
        compute='_compute_announcement_stats'
    )
    published_announcements = fields.Integer(
        string='Published',
        compute='_compute_announcement_stats'
    )
    total_announcement_reads = fields.Integer(
        string='Total Reads',
        compute='_compute_announcement_stats'
    )
    avg_read_rate = fields.Float(
        string='Avg Read Rate (%)',
        compute='_compute_announcement_stats'
    )

    # ========== UPDATE REQUEST STATS ==========
    total_update_requests = fields.Integer(
        string='Total Requests',
        compute='_compute_update_request_stats'
    )
    pending_update_requests = fields.Integer(
        string='Pending',
        compute='_compute_update_request_stats'
    )
    approved_update_requests = fields.Integer(
        string='Approved',
        compute='_compute_update_request_stats'
    )
    rejected_update_requests = fields.Integer(
        string='Rejected',
        compute='_compute_update_request_stats'
    )

    # ========== CRM STATS ==========
    total_crm_leads = fields.Integer(
        string='Total CRM Leads',
        compute='_compute_crm_stats'
    )
    agency_leads = fields.Integer(
        string='Agency Leads',
        compute='_compute_crm_stats'
    )
    converted_leads = fields.Integer(
        string='Converted',
        compute='_compute_crm_stats'
    )

    # ========== RECENT ITEMS ==========
    recent_registrations = fields.Html(
        string='Recent Registrations',
        compute='_compute_recent_items'
    )
    recent_messages = fields.Html(
        string='Recent Messages',
        compute='_compute_recent_items'
    )

    @api.depends('date_from', 'date_to')
    def _compute_registration_stats(self):
        Registration = self.env['agency.registration'].sudo()
        for rec in self:
            domain = []
            if rec.date_from:
                domain.append(('create_date', '>=', rec.date_from))
            if rec.date_to:
                domain.append(('create_date', '<=', rec.date_to))

            all_regs = Registration.search(domain)
            rec.total_registrations = len(all_regs)
            rec.pending_registrations = len(all_regs.filtered(lambda r: r.state == 'pending'))
            rec.approved_registrations = len(all_regs.filtered(lambda r: r.state == 'approved'))
            rec.rejected_registrations = len(all_regs.filtered(lambda r: r.state == 'rejected'))

            # This month
            month_start = fields.Date.today().replace(day=1)
            rec.registrations_this_month = Registration.search_count([
                ('create_date', '>=', month_start)
            ])

    @api.depends('date_from', 'date_to')
    def _compute_agency_stats(self):
        Agency = self.env['travel.agency'].sudo()
        for rec in self:
            all_agencies = Agency.search([])
            rec.total_agencies = len(all_agencies)
            rec.active_agencies = len(all_agencies.filtered(lambda a: a.state == 'active'))
            rec.suspended_agencies = len(all_agencies.filtered(lambda a: a.state == 'suspended'))
            rec.terminated_agencies = len(all_agencies.filtered(lambda a: a.state == 'terminated'))

    @api.depends('date_from', 'date_to')
    def _compute_message_stats(self):
        Conversation = self.env['agency.conversation'].sudo()
        Message = self.env['agency.message'].sudo()
        for rec in self:
            all_convs = Conversation.search([])
            rec.total_conversations = len(all_convs)
            rec.open_conversations = len(all_convs.filtered(lambda c: c.state == 'open'))

            domain = []
            if rec.date_from:
                domain.append(('create_date', '>=', rec.date_from))
            if rec.date_to:
                domain.append(('create_date', '<=', rec.date_to))

            all_msgs = Message.search(domain)
            rec.total_messages = len(all_msgs)
            rec.unread_messages = len(all_msgs.filtered(
                lambda m: m.sender_type == 'agency' and not m.is_read_by_admin
            ))

            # This month
            month_start = fields.Date.today().replace(day=1)
            rec.messages_this_month = Message.search_count([
                ('create_date', '>=', month_start)
            ])

    @api.depends('date_from', 'date_to')
    def _compute_announcement_stats(self):
        Announcement = self.env['agency.announcement'].sudo()
        Read = self.env['agency.announcement.read'].sudo()
        for rec in self:
            all_anns = Announcement.search([])
            rec.total_announcements = len(all_anns)
            rec.published_announcements = len(all_anns.filtered(lambda a: a.state == 'published'))
            rec.total_announcement_reads = Read.search_count([])

            # Calculate average read rate
            if rec.published_announcements > 0:
                total_rate = sum(all_anns.filtered(lambda a: a.state == 'published').mapped(
                    lambda a: (a.read_count / a.target_count * 100) if a.target_count > 0 else 0
                ))
                rec.avg_read_rate = total_rate / rec.published_announcements
            else:
                rec.avg_read_rate = 0

    @api.depends('date_from', 'date_to')
    def _compute_update_request_stats(self):
        Request = self.env['agency.update.request'].sudo()
        for rec in self:
            domain = []
            if rec.date_from:
                domain.append(('create_date', '>=', rec.date_from))
            if rec.date_to:
                domain.append(('create_date', '<=', rec.date_to))

            all_reqs = Request.search(domain)
            rec.total_update_requests = len(all_reqs)
            rec.pending_update_requests = len(all_reqs.filtered(lambda r: r.state == 'pending'))
            rec.approved_update_requests = len(all_reqs.filtered(lambda r: r.state == 'approved'))
            rec.rejected_update_requests = len(all_reqs.filtered(lambda r: r.state == 'rejected'))

    @api.depends('date_from', 'date_to')
    def _compute_crm_stats(self):
        Lead = self.env['crm.lead'].sudo()
        for rec in self:
            # Check if agency fields exist on crm.lead
            if 'is_agency_lead' in Lead._fields:
                rec.total_crm_leads = Lead.search_count([])
                rec.agency_leads = Lead.search_count([('is_agency_lead', '=', True)])
                rec.converted_leads = Lead.search_count([
                    ('is_agency_lead', '=', True),
                    ('agency_id', '!=', False)
                ])
            else:
                rec.total_crm_leads = Lead.search_count([])
                rec.agency_leads = 0
                rec.converted_leads = 0

    @api.depends('date_from', 'date_to')
    def _compute_recent_items(self):
        Registration = self.env['agency.registration'].sudo()
        Conversation = self.env['agency.conversation'].sudo()

        for rec in self:
            # Recent Registrations
            recent_regs = Registration.search([], limit=5, order='create_date desc')
            html = '<ul class="list-unstyled mb-0">'
            for reg in recent_regs:
                state_class = {
                    'pending': 'warning',
                    'approved': 'success',
                    'rejected': 'danger',
                    'draft': 'secondary'
                }.get(reg.state, 'secondary')
                reg_name = reg.name or f'Registration #{reg.id}'
                html += f'''
                <li class="d-flex justify-content-between align-items-center mb-2">
                    <span><strong>{reg_name}</strong></span>
                    <span class="badge bg-{state_class}">{reg.state.title()}</span>
                </li>'''
            html += '</ul>'
            rec.recent_registrations = html

            # Recent Messages
            recent_convs = Conversation.search([('state', '=', 'open')], limit=5, order='last_message_date desc')
            html = '<ul class="list-unstyled mb-0">'
            for conv in recent_convs:
                unread = conv.unread_admin_count
                badge = f'<span class="badge bg-danger">{unread}</span>' if unread > 0 else ''
                html += f'''
                <li class="d-flex justify-content-between align-items-center mb-2">
                    <span><strong>{conv.agency_id.name}</strong>: {conv.name[:30]}...</span>
                    {badge}
                </li>'''
            html += '</ul>'
            rec.recent_messages = html

    # ========== ACTIONS ==========
    def action_view_pending_registrations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pending Registrations'),
            'res_model': 'agency.registration',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'pending')],
            'target': 'current',
        }

    def action_view_open_conversations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Open Conversations'),
            'res_model': 'agency.conversation',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'open')],
            'target': 'current',
        }

    def action_view_pending_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pending Update Requests'),
            'res_model': 'agency.update.request',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'pending')],
            'target': 'current',
        }

    def action_view_agencies(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('All Agencies'),
            'res_model': 'travel.agency',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_refresh(self):
        """Refresh dashboard data"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'agency.dashboard',
            'view_mode': 'form',
            'target': 'inline',
            'flags': {'mode': 'readonly'},
        }

    @api.model
    def get_dashboard_action(self):
        """Return action to open dashboard"""
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Agency Dashboard'),
            'res_model': 'agency.dashboard',
            'view_mode': 'form',
            'res_id': dashboard.id,
            'target': 'inline',
            'flags': {'mode': 'readonly'},
        }
