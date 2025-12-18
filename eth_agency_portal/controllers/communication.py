# -*- coding: utf-8 -*-
"""
Communication Controller for Agency Portal
Handles announcements, campaigns, and messaging
"""
import logging
from datetime import datetime
from odoo import http, fields, _
from odoo.http import request
from .base import AgencyPortalBase

_logger = logging.getLogger(__name__)


class CommunicationController(AgencyPortalBase):
    """Communication controllers for agency portal"""

    # ==================== Announcements ====================

    @http.route('/agency/announcements', type='http', auth="public", website=True, csrf=False)
    def announcements_page(self, **kw):
        """Announcements list page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            if not agency_data:
                return request.redirect('/agency/login')

            # Get announcements for this agency
            announcements = self._get_agency_announcements(agency_data)

            values = self._prepare_values(
                page_name='announcements',
                announcements=announcements
            )
            return request.render('eth_agency_portal.agency_announcements', values)

        except Exception as e:
            _logger.error(f"Error in announcements page: {str(e)}", exc_info=True)
            return request.redirect('/agency/dashboard')

    @http.route('/agency/announcements/<int:announcement_id>', type='http', auth="public", website=True, csrf=False)
    def announcement_detail(self, announcement_id, **kw):
        """Announcement detail page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            user_data = self._get_current_user()
            if not agency_data:
                return request.redirect('/agency/login')

            announcement = request.env['agency.announcement'].sudo().browse(announcement_id)
            if not announcement.exists() or announcement.state != 'published':
                return request.redirect('/agency/announcements')

            # Mark as read
            self._mark_announcement_read(announcement, agency_data, user_data)

            # Get content in user's language
            lang = agency_data.get('preferred_language', 'en')
            content = announcement.get_content_by_language(lang)

            values = self._prepare_values(
                page_name='announcement_detail',
                announcement=announcement,
                content=content,
                lang=lang
            )
            return request.render('eth_agency_portal.agency_announcement_detail', values)

        except Exception as e:
            _logger.error(f"Error in announcement detail: {str(e)}", exc_info=True)
            return request.redirect('/agency/announcements')

    def _get_agency_announcements(self, agency_data):
        """Get announcements targeted at this agency"""
        Announcement = request.env['agency.announcement'].sudo()
        Read = request.env['agency.announcement.read'].sudo()
        today = fields.Date.today()

        # Base domain: published, within date range
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

        # Get read announcement IDs for this agency
        read_records = Read.search([('agency_id', '=', agency_id)])
        read_announcement_ids = read_records.mapped('announcement_id').ids

        result = []
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
                result.append({
                    'id': ann.id,
                    'name': ann.name,
                    'announcement_type': ann.announcement_type,
                    'image': ann.image,
                    'video_url': ann.video_url,
                    'video_embed_url': ann.get_video_embed_url() if ann.video_url else False,
                    'has_video': ann.has_video,
                    'start_date': ann.start_date,
                    'summary': ann.get_summary_by_language(agency_data.get('preferred_language', 'en')),
                    'is_read': ann.id in read_announcement_ids,
                    'priority': ann.priority,
                })

        return result

    def _mark_announcement_read(self, announcement, agency_data, user_data):
        """Mark announcement as read by agency"""
        try:
            Read = request.env['agency.announcement.read'].sudo()
            existing = Read.search([
                ('announcement_id', '=', announcement.id),
                ('agency_id', '=', agency_data.get('id'))
            ], limit=1)

            if not existing:
                Read.create({
                    'announcement_id': announcement.id,
                    'agency_id': agency_data.get('id'),
                    'user_id': user_data.get('id') if user_data else False,
                })
        except Exception as e:
            _logger.error(f"Error marking announcement read: {e}")

    # ==================== Messages ====================

    @http.route('/agency/messages', type='http', auth="public", website=True, csrf=False)
    def messages_page(self, **kw):
        """Messages/Conversations list page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            if not agency_data:
                return request.redirect('/agency/login')

            # Get conversations for this agency
            conversations = request.env['agency.conversation'].sudo().search([
                ('agency_id', '=', agency_data.get('id'))
            ], order='last_message_date desc')

            values = self._prepare_values(
                page_name='messages',
                conversations=conversations
            )
            return request.render('eth_agency_portal.agency_messages', values)

        except Exception as e:
            _logger.error(f"Error in messages page: {str(e)}", exc_info=True)
            return request.redirect('/agency/dashboard')

    @http.route('/agency/messages/<int:conversation_id>', type='http', auth="public", website=True, csrf=False)
    def conversation_detail(self, conversation_id, **kw):
        """Conversation detail page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            if not agency_data:
                return request.redirect('/agency/login')

            conversation = request.env['agency.conversation'].sudo().browse(conversation_id)
            if not conversation.exists() or conversation.agency_id.id != agency_data.get('id'):
                return request.redirect('/agency/messages')

            # Mark admin messages as read by agency
            conversation.message_ids.filtered(
                lambda m: m.sender_type == 'admin' and not m.is_read_by_agency
            ).mark_as_read_agency()

            values = self._prepare_values(
                page_name='conversation_detail',
                conversation=conversation,
                messages=conversation.message_ids.sorted('create_date')
            )
            return request.render('eth_agency_portal.agency_conversation_detail', values)

        except Exception as e:
            _logger.error(f"Error in conversation detail: {str(e)}", exc_info=True)
            return request.redirect('/agency/messages')

    @http.route('/agency/messages/new', type='http', auth="public", website=True, csrf=False)
    def new_conversation_page(self, **kw):
        """New conversation page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            if not agency_data:
                return request.redirect('/agency/login')

            values = self._prepare_values(page_name='new_message')
            return request.render('eth_agency_portal.agency_new_conversation', values)

        except Exception as e:
            _logger.error(f"Error in new conversation page: {str(e)}", exc_info=True)
            return request.redirect('/agency/messages')

    # ==================== API Endpoints ====================

    @http.route('/agency/api/messages/send', type='json', auth='public', methods=['POST'], csrf=False)
    def send_message(self, conversation_id=None, subject=None, message=None, **kw):
        """Send a message"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            user_data = self._get_current_user()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            if not message:
                return {'success': False, 'error': 'Message is required'}

            Conversation = request.env['agency.conversation'].sudo()
            Message = request.env['agency.message'].sudo()

            # Create new conversation or use existing
            if conversation_id:
                conversation = Conversation.browse(int(conversation_id))
                if not conversation.exists() or conversation.agency_id.id != agency_data.get('id'):
                    return {'success': False, 'error': 'Conversation not found'}
            else:
                if not subject:
                    return {'success': False, 'error': 'Subject is required for new conversation'}

                conversation = Conversation.create({
                    'name': subject,
                    'agency_id': agency_data.get('id'),
                    'agency_user_id': user_data.get('id') if user_data else False,
                    'state': 'open',
                })

            # Create message
            Message.create({
                'conversation_id': conversation.id,
                'body': message,
                'sender_type': 'agency',
                'sender_agency_user_id': user_data.get('id') if user_data else False,
            })

            return {
                'success': True,
                'conversation_id': conversation.id,
                'message': 'Message sent successfully'
            }

        except Exception as e:
            _logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/announcements/unread-count', type='json', auth='public', methods=['POST'], csrf=False)
    def get_unread_count(self, **kw):
        """Get unread announcements count"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            announcements = self._get_agency_announcements(agency_data)
            unread_count = len([a for a in announcements if not a.get('is_read')])

            return {
                'success': True,
                'unread_count': unread_count,
                'total_count': len(announcements)
            }

        except Exception as e:
            _logger.error(f"Error getting unread count: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/messages/unread-count', type='json', auth='public', methods=['POST'], csrf=False)
    def get_unread_messages_count(self, **kw):
        """Get unread messages count"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            conversations = request.env['agency.conversation'].sudo().search([
                ('agency_id', '=', agency_data.get('id'))
            ])

            unread_count = sum(conversations.mapped('unread_agency_count'))

            return {
                'success': True,
                'unread_count': unread_count
            }

        except Exception as e:
            _logger.error(f"Error getting unread messages count: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/announcements/dashboard', type='json', auth='public', methods=['POST'], csrf=False)
    def get_dashboard_announcements(self, limit=5, **kw):
        """Get announcements for dashboard display"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            announcements = self._get_agency_announcements(agency_data)

            # Separate by type and limit
            all_announcements = [a for a in announcements if a.get('announcement_type') == 'announcement'][:limit]
            campaigns = [a for a in announcements if a.get('announcement_type') == 'campaign'][:limit]

            # Count unread
            unread_announcements = len([a for a in announcements if not a.get('is_read') and a.get('announcement_type') == 'announcement'])
            unread_campaigns = len([a for a in announcements if not a.get('is_read') and a.get('announcement_type') == 'campaign'])

            return {
                'success': True,
                'announcements': all_announcements,
                'campaigns': campaigns,
                'unread_announcements': unread_announcements,
                'unread_campaigns': unread_campaigns,
                'total_unread': unread_announcements + unread_campaigns
            }

        except Exception as e:
            _logger.error(f"Error getting dashboard announcements: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
