# -*- coding: utf-8 -*-
import logging
from odoo import http, fields, _
from odoo.http import request
from .base import AgencyPortalBase, require_auth, auto_language

_logger = logging.getLogger(__name__)


class DashboardController(AgencyPortalBase):
    """Dashboard controller"""

    @http.route('/agency/dashboard', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_dashboard(self, **kwargs):
        """Agency dashboard page"""
        try:
            # Get user data first
            user_data = self._get_current_user()
            if not user_data:
                _logger.warning("Dashboard: No user data found")
                return request.redirect('/agency/login')

            # Get permissions safely
            permissions = user_data.get('permissions', {})
            _logger.info(f"Dashboard permissions: {permissions}")

            # Check permissions (more lenient - if no permission system, allow)
            if permissions and not permissions.get('dashboard_view', True):
                _logger.warning(f"User {user_data.get('name')} doesn't have dashboard_view permission")
                values = self._prepare_values(
                    page_name='access_denied',
                    message=_('You do not have permission to view the dashboard.')
                )
                return request.render('eth_agency_portal.agency_access_denied', values)

            # Get agency data
            agency_data = self._get_agency_data()

            # Get statistics (example - replace with real logic)
            stats = {
                'total_bookings': 150,
                'pending_bookings': 12,
                'total_sales': 50000,
                'month_sales': 15000,
            }

            # Get announcements and campaigns for dashboard
            announcements, campaigns, unread_count = self._get_dashboard_announcements(agency_data)

            # Prepare values once
            values = self._prepare_values(
                page_name='dashboard',
                stats=stats,
                dashboard_announcements=announcements,
                dashboard_campaigns=campaigns,
                unread_announcements_count=unread_count,
            )

            return request.render('eth_agency_portal.agency_dashboard', values)

        except Exception as e:
            _logger.error(f"Error in dashboard: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            # Redirect to login on any error
            return request.redirect('/agency/login')

    def _get_dashboard_announcements(self, agency_data, limit=4):
        """Get announcements and campaigns for dashboard"""
        try:
            Announcement = request.env['agency.announcement'].sudo()
            Read = request.env['agency.announcement.read'].sudo()
            today = fields.Date.today()

            # Base domain
            domain = [
                ('state', '=', 'published'),
                ('start_date', '<=', today),
                '|',
                ('end_date', '=', False),
                ('end_date', '>=', today),
            ]

            all_announcements = Announcement.search(domain, order='priority desc, sequence, create_date desc')

            # Filter by targeting
            agency_id = agency_data.get('id')
            agency = request.env['travel.agency'].sudo().browse(agency_id)

            # Get read announcement IDs
            read_records = Read.search([('agency_id', '=', agency_id)])
            read_announcement_ids = read_records.mapped('announcement_id').ids

            lang = agency_data.get('preferred_language', 'en')
            announcements = []
            campaigns = []
            unread_count = 0

            for ann in all_announcements:
                include = False
                if ann.target_type == 'all':
                    include = True
                elif ann.target_type == 'selected' and agency in ann.agency_ids:
                    include = True
                elif ann.target_type == 'by_group' and agency.agency_group_id in ann.agency_group_ids:
                    include = True
                elif ann.target_type == 'by_country' and agency.country_id in ann.country_ids:
                    include = True
                elif ann.target_type == 'by_language' and agency.preferred_language == ann.target_languages:
                    include = True

                if include:
                    is_read = ann.id in read_announcement_ids
                    if not is_read:
                        unread_count += 1

                    item = {
                        'id': ann.id,
                        'name': ann.name,
                        'announcement_type': ann.announcement_type,
                        'image': ann.image,
                        'video_url': ann.video_url,
                        'video_embed_url': ann.get_video_embed_url() if ann.video_url else False,
                        'has_video': ann.has_video,
                        'start_date': ann.start_date,
                        'summary': ann.get_summary_by_language(lang),
                        'is_read': is_read,
                        'priority': ann.priority,
                    }

                    if ann.announcement_type == 'announcement' and len(announcements) < limit:
                        announcements.append(item)
                    elif ann.announcement_type == 'campaign' and len(campaigns) < limit:
                        campaigns.append(item)

            return announcements, campaigns, unread_count

        except Exception as e:
            _logger.error(f"Error getting dashboard announcements: {str(e)}", exc_info=True)
            return [], [], 0
