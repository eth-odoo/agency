# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgencyAnnouncement(models.Model):
    _name = 'agency.announcement'
    _description = 'Agency Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Title',
        required=True,
        tracking=True
    )

    announcement_type = fields.Selection([
        ('announcement', 'Announcement'),
        ('campaign', 'Campaign'),
    ], string='Type', required=True, default='announcement', tracking=True)

    # Multi-language content
    content_tr = fields.Html(string='Content (Turkish)')
    content_en = fields.Html(string='Content (English)')
    content_de = fields.Html(string='Content (German)')
    content_fr = fields.Html(string='Content (French)')

    # Summary for dashboard preview
    summary_tr = fields.Text(string='Summary (Turkish)', help='Short summary for dashboard')
    summary_en = fields.Text(string='Summary (English)')
    summary_de = fields.Text(string='Summary (German)')
    summary_fr = fields.Text(string='Summary (French)')

    # Media
    image = fields.Binary(string='Image')
    image_filename = fields.Char(string='Image Filename')
    video_url = fields.Char(
        string='Video URL',
        help='YouTube or Vimeo video URL. Supports formats like: '
             'https://www.youtube.com/watch?v=VIDEO_ID, '
             'https://youtu.be/VIDEO_ID, '
             'https://vimeo.com/VIDEO_ID'
    )
    has_video = fields.Boolean(
        string='Has Video',
        compute='_compute_has_video',
        store=True
    )
    link = fields.Char(string='External Link')
    link_text = fields.Char(string='Link Text', default='Learn More')

    # Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    end_date = fields.Date(
        string='End Date',
        tracking=True
    )

    # Targeting
    target_type = fields.Selection([
        ('all', 'All Agencies'),
        ('selected', 'Selected Agencies'),
        ('by_group', 'By Agency Group'),
        ('by_country', 'By Country'),
        ('by_language', 'By Language'),
    ], string='Target', default='all', required=True, tracking=True)

    # Target selections
    agency_ids = fields.Many2many(
        'travel.agency',
        'announcement_agency_rel',
        'announcement_id',
        'agency_id',
        string='Selected Agencies'
    )
    agency_group_ids = fields.Many2many(
        'agency.group',
        'announcement_group_rel',
        'announcement_id',
        'group_id',
        string='Agency Groups'
    )
    country_ids = fields.Many2many(
        'res.country',
        'announcement_country_rel',
        'announcement_id',
        'country_id',
        string='Countries'
    )
    target_languages = fields.Selection([
        ('tr', 'Turkish'),
        ('en', 'English'),
        ('de', 'German'),
        ('fr', 'French'),
    ], string='Target Language')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)

    # Priority/Order
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0')
    sequence = fields.Integer(string='Sequence', default=10)

    # Tracking
    read_ids = fields.One2many(
        'agency.announcement.read',
        'announcement_id',
        string='Read Records'
    )
    read_count = fields.Integer(
        string='Read Count',
        compute='_compute_read_stats'
    )
    unread_count = fields.Integer(
        string='Unread Count',
        compute='_compute_read_stats'
    )
    target_count = fields.Integer(
        string='Target Agency Count',
        compute='_compute_target_agencies'
    )

    # Creator
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('video_url')
    def _compute_has_video(self):
        for rec in self:
            rec.has_video = bool(rec.video_url)

    @api.depends('read_ids', 'target_type', 'agency_ids', 'agency_group_ids', 'country_ids', 'target_languages')
    def _compute_read_stats(self):
        for rec in self:
            rec.read_count = len(rec.read_ids)
            target_agencies = rec._get_target_agencies()
            rec.unread_count = len(target_agencies) - rec.read_count

    @api.depends('target_type', 'agency_ids', 'agency_group_ids', 'country_ids', 'target_languages')
    def _compute_target_agencies(self):
        for rec in self:
            rec.target_count = len(rec._get_target_agencies())

    def _get_target_agencies(self):
        """Get list of target agencies based on targeting settings"""
        self.ensure_one()
        Agency = self.env['travel.agency'].sudo()

        if self.target_type == 'all':
            return Agency.search([('state', '=', 'active')])

        elif self.target_type == 'selected':
            return self.agency_ids.filtered(lambda a: a.state == 'active')

        elif self.target_type == 'by_group':
            return Agency.search([
                ('state', '=', 'active'),
                ('agency_group_id', 'in', self.agency_group_ids.ids)
            ])

        elif self.target_type == 'by_country':
            return Agency.search([
                ('state', '=', 'active'),
                ('country_id', 'in', self.country_ids.ids)
            ])

        elif self.target_type == 'by_language':
            return Agency.search([
                ('state', '=', 'active'),
                ('preferred_language', '=', self.target_languages)
            ])

        return Agency.browse()

    def action_publish(self):
        """Publish the announcement"""
        self.write({'state': 'published'})

    def action_archive(self):
        """Archive the announcement"""
        self.write({'state': 'archived'})

    def action_draft(self):
        """Set back to draft"""
        self.write({'state': 'draft'})

    def action_view_reads(self):
        """View read records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Read Records'),
            'res_model': 'agency.announcement.read',
            'view_mode': 'tree,form',
            'domain': [('announcement_id', '=', self.id)],
            'context': {'default_announcement_id': self.id},
        }

    def get_content_by_language(self, lang='en'):
        """Get content in specified language with fallback to English"""
        self.ensure_one()
        content_field = f'content_{lang}'
        content = getattr(self, content_field, None)
        if not content:
            content = self.content_en or self.content_tr
        return content

    def get_summary_by_language(self, lang='en'):
        """Get summary in specified language with fallback"""
        self.ensure_one()
        summary_field = f'summary_{lang}'
        summary = getattr(self, summary_field, None)
        if not summary:
            summary = self.summary_en or self.summary_tr
        return summary

    def get_video_embed_url(self):
        """Convert video URL to embeddable format"""
        self.ensure_one()
        if not self.video_url:
            return False

        url = self.video_url.strip()

        # YouTube patterns
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]+)',
        ]

        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f'https://www.youtube.com/embed/{video_id}'

        # Vimeo patterns
        vimeo_patterns = [
            r'(?:https?://)?(?:www\.)?vimeo\.com/(\d+)',
            r'(?:https?://)?player\.vimeo\.com/video/(\d+)',
        ]

        for pattern in vimeo_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f'https://player.vimeo.com/video/{video_id}'

        # Return original URL if no pattern matches (might be direct video)
        return url


class AgencyAnnouncementRead(models.Model):
    _name = 'agency.announcement.read'
    _description = 'Agency Announcement Read Record'
    _order = 'read_date desc'

    announcement_id = fields.Many2one(
        'agency.announcement',
        string='Announcement',
        required=True,
        ondelete='cascade'
    )
    agency_id = fields.Many2one(
        'travel.agency',
        string='Agency',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'agency.user',
        string='User',
        ondelete='set null'
    )
    read_date = fields.Datetime(
        string='Read Date',
        default=fields.Datetime.now,
        required=True
    )

    _sql_constraints = [
        ('unique_read', 'UNIQUE(announcement_id, agency_id)',
         'This agency has already read this announcement.')
    ]
