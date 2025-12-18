# -*- coding: utf-8 -*-
import logging
import functools
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class LanguageManager:
    """Centralized language management with caching"""

    _cache = {
        'languages': None,
        'translations': {},
    }

    @classmethod
    def get_available_languages(cls):
        """Get available languages with caching"""
        if cls._cache['languages'] is None:
            langs = request.env['res.lang'].sudo().search([('active', '=', True)])
            cls._cache['languages'] = [(lang.code, lang.name) for lang in langs]
        return cls._cache['languages']

    @classmethod
    def get_current_language(cls):
        """
        Get current language with CORRECT priority:
        1. Session (user's explicit choice) - HIGHEST PRIORITY
        2. Cookie (frontend_lang) - for website persistence
        3. Agency default (if no session preference)
        4. System default (fallback)
        """
        # 1. CHECK SESSION FIRST (user's explicit choice)
        session_lang = request.session.get('agency_lang')
        if session_lang:
            _logger.debug(f"Language from session: {session_lang}")
            return session_lang

        # 2. Check frontend_lang cookie
        try:
            cookie_lang = request.httprequest.cookies.get('frontend_lang')
            if cookie_lang:
                _logger.debug(f"Language from cookie: {cookie_lang}")
                # Also set in session for consistency
                request.session['agency_lang'] = cookie_lang
                return cookie_lang
        except Exception as e:
            _logger.debug(f"Error reading cookie: {str(e)}")

        # 3. Check agency default (only if no session preference)
        try:
            agency_id = request.session.get('agency_id')
            if agency_id:
                agency = request.env['travel.agency'].sudo().browse(agency_id)
                if agency.exists() and hasattr(agency, 'default_language') and agency.default_language:
                    _logger.debug(f"Language from agency default: {agency.default_language}")
                    return agency.default_language
        except Exception as e:
            _logger.warning(f"Error getting agency language: {str(e)}")

        # 4. Fallback to English
        _logger.debug("Language fallback to en_US")
        return 'en_US'

    @classmethod
    def set_language(cls, lang_code):
        """Set language in session and context"""
        try:
            # Normalize language code
            lang_mapping = {
                'tr-TR': 'tr_TR', 'tr': 'tr_TR',
                'en-US': 'en_US', 'en': 'en_US',
                'TR': 'tr_TR', 'EN': 'en_US',
            }
            normalized_lang = lang_mapping.get(lang_code, lang_code)

            _logger.info(f"Setting language: {lang_code} -> {normalized_lang}")

            # Validate language exists
            available_langs = [code for code, name in cls.get_available_languages()]
            if normalized_lang not in available_langs:
                _logger.warning(f"Invalid language: {normalized_lang}. Available: {available_langs}")
                return False

            # Update session (THIS IS THE MOST IMPORTANT - user's explicit choice)
            request.session['agency_lang'] = normalized_lang

            # Also update context for immediate effect
            request.update_context(lang=normalized_lang)

            _logger.info(f"Language successfully set to: {normalized_lang}")

            return True

        except Exception as e:
            _logger.error(f"Error setting language: {str(e)}")
            return False

    @classmethod
    def clear_cache(cls):
        """Clear language cache"""
        cls._cache = {'languages': None, 'translations': {}}


def require_auth(redirect_url='/agency/login'):
    """Decorator to require authentication"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not request.session.get('agency_token'):
                _logger.info(f"Unauthorized access attempt to {func.__name__}")
                return request.redirect(redirect_url)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def auto_language(func):
    """
    Decorator to automatically handle language setup
    Sets the request context language based on user preference
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            # Get current language from LanguageManager (respects priority)
            current_lang = LanguageManager.get_current_language()

            # ALWAYS set context to current language
            request.update_context(lang=current_lang)

            # Also set frontend_lang for website templates
            if hasattr(request, 'frontend_lang'):
                request.frontend_lang = current_lang

            # Force env to use the language
            request.env = request.env(context=dict(request.env.context, lang=current_lang))

            _logger.debug(f"auto_language: Set context to {current_lang}")

            return func(self, *args, **kwargs)

        except Exception as e:
            _logger.error(f"Error in auto_language: {str(e)}")
            return func(self, *args, **kwargs)
    return wrapper


class AgencyPortalBase(http.Controller):
    """Base controller with common methods"""

    # ==================== Authentication Methods ====================

    def _is_authenticated(self):
        """Check if user is authenticated"""
        return bool(request.session.get('agency_token'))

    def _get_current_user(self):
        """Get current user data with caching in request"""
        if not hasattr(request, '_cached_user_data'):
            try:
                token = request.session.get('agency_token')
                if not token:
                    _logger.debug("No token found in session")
                    request._cached_user_data = None
                    return None

                auth_service = request.env['agency.auth.service'].sudo()
                result = auth_service.validate_token(token)

                if result.get('success'):
                    user_data = result.get('user_data', {})
                    _logger.debug(f"User authenticated: {user_data.get('email', 'unknown')}")
                    request._cached_user_data = user_data
                else:
                    _logger.warning(f"Token validation failed: {result.get('message')}")
                    self._clear_session()
                    request._cached_user_data = None
            except Exception as e:
                _logger.error(f"Error getting current user: {str(e)}")
                request._cached_user_data = None

        return request._cached_user_data

    def _has_permission(self, permission):
        """Check if current user has permission"""
        try:
            user_data = self._get_current_user()
            if not user_data:
                return False

            permissions = user_data.get('permissions', {})
            if not permissions:
                return True

            return permissions.get(permission, False)

        except Exception as e:
            _logger.error(f"Error checking permission '{permission}': {str(e)}")
            return False

    def _get_agency_id(self):
        """Get current agency ID"""
        agency_id = request.session.get('agency_id')
        if agency_id:
            return agency_id

        user_data = self._get_current_user()
        return user_data.get('agency_id') if user_data else None

    def _clear_session(self):
        """Clear all session data"""
        _logger.info("Clearing session data")
        request.session.pop('agency_token', None)
        request.session.pop('agency_user_id', None)
        request.session.pop('agency_id', None)
        request.session.pop('agency_lang', None)

    # ==================== Agency Methods ====================

    def _get_agency_data(self, agency_id=None):
        """Get agency data with caching"""
        if not hasattr(request, '_cached_agency_data'):
            try:
                if not agency_id:
                    agency_id = self._get_agency_id()

                if not agency_id:
                    _logger.debug("No agency ID found")
                    request._cached_agency_data = None
                    return None

                agency = request.env['travel.agency'].sudo().browse(agency_id)
                if not agency.exists():
                    _logger.warning(f"Agency {agency_id} not found")
                    request._cached_agency_data = None
                    return None

                # Get membership purposes
                membership_purposes = []
                if agency.membership_purpose_ids:
                    membership_purposes = agency.membership_purpose_ids.mapped('name')

                request._cached_agency_data = {
                    'id': agency.id,
                    'name': agency.name,
                    'partner_id': agency.partner_id.id if agency.partner_id else None,
                    'membership_purposes': membership_purposes,
                    'has_bonus': not membership_purposes or 'Bonus' in membership_purposes,
                    'has_sales': not membership_purposes or 'Sales' in membership_purposes or 'Satış' in membership_purposes,
                    'has_tickets': not membership_purposes or 'Ticket' in membership_purposes or 'Tickets' in membership_purposes or 'Ticket Sales' in membership_purposes or 'Bilet' in membership_purposes,
                    'default_language': agency.default_language if hasattr(agency, 'default_language') else None,
                }

                _logger.debug(f"Agency data loaded: {agency.name}")

            except Exception as e:
                _logger.error(f"Error getting agency data: {str(e)}")
                request._cached_agency_data = None

        return request._cached_agency_data

    # ==================== Template Preparation ====================

    def _prepare_values(self, **kwargs):
        """Prepare common template values"""
        try:
            user_data = self._get_current_user()
            agency_data = self._get_agency_data()
            current_lang = LanguageManager.get_current_language()

            # Get translatable terms for JavaScript
            translatable_terms = self._get_translatable_terms()

            custom_values = {
                'user_data': user_data,
                'agency_data': agency_data,
                'current_language': current_lang,
                'available_languages': LanguageManager.get_available_languages(),
                'translatable_terms': translatable_terms,
                '_': _,
            }

            custom_values.update(kwargs)
            return custom_values

        except Exception as e:
            _logger.error(f"Error preparing values: {str(e)}")
            return {
                'user_data': None,
                'agency_data': None,
                'current_language': 'en_US',
                'available_languages': [],
                'translatable_terms': {},
                '_': _,
                **kwargs
            }

    def _get_translatable_terms(self):
        """Get common translatable terms for templates"""
        return {
            'dashboard': _('Dashboard'),
            'users': _('Users'),
            'settings': _('Settings'),
            'logout': _('Logout'),
            'reports': _('Reports'),
            'bookings': _('Bookings'),
            'bonus': _('Bonus'),
            'tickets': _('Tickets'),
            'messages': _('Messages'),
            'announcements': _('Announcements'),
            'save': _('Save'),
            'cancel': _('Cancel'),
            'confirm': _('Confirm'),
            'delete': _('Delete'),
            'edit': _('Edit'),
            'view': _('View'),
            'loading': _('Loading...'),
            'error': _('Error'),
            'success': _('Success'),
            'warning': _('Warning'),
        }

    # ==================== Language Routes ====================

    @http.route('/agency/change-language', type='json', auth='public', methods=['POST'], csrf=False)
    def change_language(self, lang_code):
        """Change session language"""
        try:
            _logger.info(f"=== CHANGE LANGUAGE REQUEST ===")
            _logger.info(f"Requested language: {lang_code}")

            success = LanguageManager.set_language(lang_code)

            if success:
                new_lang = LanguageManager.get_current_language()

                # Also set frontend_lang cookie for website templates
                response_data = {
                    'success': True,
                    'message': _('Language changed successfully'),
                    'new_lang': new_lang
                }

                # Set cookie for website language
                request.future_response.set_cookie(
                    'frontend_lang',
                    new_lang,
                    max_age=365*24*60*60,  # 1 year
                    httponly=False
                )

                return response_data
            else:
                return {
                    'success': False,
                    'message': _('Invalid language code') + f': {lang_code}'
                }

        except Exception as e:
            _logger.error(f"Error changing language: {str(e)}")
            return {'success': False, 'message': str(e)}

    @http.route('/agency/get-languages', type='json', auth='public', methods=['POST'], csrf=False)
    def get_languages(self):
        """Get available languages"""
        try:
            return {
                'success': True,
                'languages': LanguageManager.get_available_languages(),
                'current': LanguageManager.get_current_language(),
            }
        except Exception as e:
            _logger.error(f"Error getting languages: {str(e)}")
            return {'success': False, 'message': str(e)}

    @http.route('/agency/set-language/<string:lang_code>', type='http', auth='public', website=True, csrf=False)
    def set_language_http(self, lang_code, redirect_url=None, **kwargs):
        """HTTP endpoint to change language with cookie support"""
        try:
            _logger.info(f"=== SET LANGUAGE HTTP ===")
            _logger.info(f"Language: {lang_code}, Redirect: {redirect_url}")

            success = LanguageManager.set_language(lang_code)

            if success:
                new_lang = LanguageManager.get_current_language()
                _logger.info(f"Language set to: {new_lang}")

                # Determine redirect URL
                if not redirect_url:
                    redirect_url = request.httprequest.referrer or '/agency/dashboard'

                # Create response with redirect
                response = request.redirect(redirect_url)

                # Set frontend_lang cookie
                response.set_cookie(
                    'frontend_lang',
                    new_lang,
                    max_age=365*24*60*60,  # 1 year
                    httponly=False
                )

                return response
            else:
                return request.redirect(redirect_url or '/agency/dashboard')

        except Exception as e:
            _logger.error(f"Error setting language: {str(e)}")
            return request.redirect('/agency/dashboard')
