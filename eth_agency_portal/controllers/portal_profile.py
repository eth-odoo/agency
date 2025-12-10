# -*- coding: utf-8 -*-
"""
Profile Portal Controller - Agency profile, users, settings
"""
import logging
from odoo import http, _
from odoo.http import request
from .portal_main import PortalMain

_logger = logging.getLogger(__name__)


class PortalProfile(PortalMain):
    """Portal controller for profile management"""

    # ==================== Profile ====================

    @http.route('/agency/profile', type='http', auth='public', website=True)
    def portal_profile(self, **kwargs):
        """Agency profile page"""
        if not self._check_login():
            return request.redirect('/agency/login')

        user = self._get_agency_user()
        agency = user.agency_id if user else None

        # Get interested hotels from Travel API
        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        interested_hotels = []
        config = api_client._get_api_config()
        if config.get('base_url'):
            result = api_client.get_agency_interested_hotels(token)
            if result.get('success') and result.get('data'):
                interested_hotels = result['data']

        context = self._portal_context(
            interested_hotels=interested_hotels,
            message=kwargs.get('message'),
            page='profile',
        )

        return request.render('eth_agency_portal.portal_profile', context)

    # ==================== Users ====================

    @http.route('/agency/users', type='http', auth='public', website=True)
    def portal_users(self, **kwargs):
        """Agency users list"""
        if not self._check_login():
            return request.redirect('/agency/login')

        user = self._get_agency_user()

        # Only master users can view all users
        if not user or not user.is_master:
            return request.redirect('/agency/dashboard')

        agency = user.agency_id
        users = request.env['agency.user'].sudo().search([
            ('agency_id', '=', agency.id),
            ('active', '=', True)
        ])

        context = self._portal_context(
            users=users,
            message=kwargs.get('message'),
            page='users',
        )

        return request.render('eth_agency_portal.portal_users', context)

    @http.route('/agency/users/<int:user_id>', type='http', auth='public', website=True)
    def portal_user_detail(self, user_id, **kwargs):
        """User detail page"""
        if not self._check_login():
            return request.redirect('/agency/login')

        current_user = self._get_agency_user()

        # Can view own profile or if master
        target_user = request.env['agency.user'].sudo().browse(user_id)
        if not target_user.exists():
            return request.redirect('/agency/users')

        if current_user.id != user_id and not current_user.is_master:
            return request.redirect('/agency/dashboard')

        if target_user.agency_id.id != current_user.agency_id.id:
            return request.redirect('/agency/dashboard')

        context = self._portal_context(
            target_user=target_user,
            can_edit=current_user.is_master or current_user.id == user_id,
            page='users',
        )

        return request.render('eth_agency_portal.portal_user_detail', context)

    # ==================== Change Password ====================

    @http.route('/agency/change-password', type='http', auth='public', website=True)
    def portal_change_password(self, **kwargs):
        """Change password page"""
        if not self._check_login():
            return request.redirect('/agency/login')

        context = self._portal_context(
            error=kwargs.get('error'),
            success=kwargs.get('success'),
            page='profile',
        )

        return request.render('eth_agency_portal.portal_change_password', context)

    @http.route('/agency/change-password', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_change_password_submit(self, **kwargs):
        """Handle password change"""
        if not self._check_login():
            return request.redirect('/agency/login')

        current_password = kwargs.get('current_password', '')
        new_password = kwargs.get('new_password', '')
        confirm_password = kwargs.get('confirm_password', '')

        if not current_password:
            return request.redirect('/agency/change-password?error=current_required')

        if not new_password or len(new_password) < 8:
            return request.redirect('/agency/change-password?error=invalid_new_password')

        if new_password != confirm_password:
            return request.redirect('/agency/change-password?error=password_mismatch')

        user = self._get_agency_user()
        auth_service = request.env['agency.auth.service'].sudo()

        # Verify current password
        result = auth_service.authenticate_user(user.email, current_password)
        if not result.get('success'):
            return request.redirect('/agency/change-password?error=wrong_current_password')

        # Update password
        try:
            user.sudo().write({'password': new_password})
            return request.redirect('/agency/change-password?success=1')
        except Exception as e:
            _logger.error(f"Password change error: {str(e)}")
            return request.redirect('/agency/change-password?error=failed')

    # ==================== Settings ====================

    @http.route('/agency/settings', type='http', auth='public', website=True)
    def portal_settings(self, **kwargs):
        """Agency settings page"""
        if not self._check_login():
            return request.redirect('/agency/login')

        user = self._get_agency_user()

        # Only master users can access settings
        if not user or not user.is_master:
            return request.redirect('/agency/dashboard')

        context = self._portal_context(
            message=kwargs.get('message'),
            page='settings',
        )

        return request.render('eth_agency_portal.portal_settings', context)

    @http.route('/agency/settings/language', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_settings_language(self, **kwargs):
        """Update agency language setting"""
        if not self._check_login():
            return request.redirect('/agency/login')

        user = self._get_agency_user()
        if not user or not user.is_master:
            return request.redirect('/agency/dashboard')

        language = kwargs.get('language', 'en_US')
        agency = user.agency_id

        try:
            agency.sudo().write({'default_language': language})
            return request.redirect('/agency/settings?message=language_updated')
        except Exception as e:
            _logger.error(f"Language update error: {str(e)}")
            return request.redirect('/agency/settings?message=update_failed')

    # ==================== Interested Hotels ====================

    @http.route('/agency/hotels', type='http', auth='public', website=True)
    def portal_hotels(self, **kwargs):
        """View/manage interested hotels"""
        if not self._check_login():
            return request.redirect('/agency/login')

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()
        config = api_client._get_api_config()

        # Current interested hotels
        interested_hotels = []
        if config.get('base_url'):
            result = api_client.get_agency_interested_hotels(token)
            if result.get('success') and result.get('data'):
                interested_hotels = result['data']

        # Available hotels (for adding new interests)
        available_hotels = []
        if config.get('base_url'):
            result = api_client.get_hotels()
            if result.get('success') and result.get('data'):
                available_hotels = result['data'].get('hotels', [])

        # Get countries for filter
        countries = []
        if config.get('base_url'):
            result = api_client.get_countries()
            if result.get('success') and result.get('data'):
                countries = result['data']

        context = self._portal_context(
            interested_hotels=interested_hotels,
            available_hotels=available_hotels,
            countries=countries,
            message=kwargs.get('message'),
            page='hotels',
        )

        return request.render('eth_agency_portal.portal_hotels', context)
