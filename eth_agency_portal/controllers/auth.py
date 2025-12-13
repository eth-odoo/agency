# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase, auto_language, LanguageManager

_logger = logging.getLogger(__name__)


class AgencyAuthController(AgencyPortalBase):
    """Authentication related controllers"""

    @http.route('/agency/login', type='http', auth="public", website=True, csrf=False)
    @auto_language
    def agency_login(self, **kwargs):
        """Agency login page"""
        # If already logged in, redirect to dashboard
        if self._is_authenticated():
            return request.redirect('/agency/dashboard')

        # Prepare values dictionary
        values = {
            'current_language': LanguageManager.get_current_language(),
            'available_languages': LanguageManager.get_available_languages(),
        }

        # Check for password reset success message
        if kwargs.get('password_reset') == 'success':
            values['success'] = _('Password reset successfully. You can now login with your new password.')

        # Handle login form submission
        if request.httprequest.method == 'POST':
            email = kwargs.get('email', '').strip()
            password = kwargs.get('password', '')

            if email and password:
                try:
                    auth_service = request.env['agency.auth.service'].sudo()
                    result = auth_service.authenticate_user(email, password)

                    if result['success']:
                        # Store in session
                        request.session['agency_token'] = result['token']
                        request.session['agency_user_id'] = result['user_id']
                        request.session['agency_id'] = result['user_data']['agency_id']

                        # Set agency default language if available
                        agency = self._get_agency_data(result['user_data']['agency_id'])
                        if agency and agency.get('default_language'):
                            request.session['agency_lang'] = agency['default_language']
                            _logger.info(f"Set agency default language on login: {agency['default_language']}")

                        # Redirect to dashboard
                        return request.redirect('/agency/dashboard')
                    else:
                        values['error'] = result['message']
                except Exception as e:
                    _logger.error(f"Login error: {str(e)}")
                    values['error'] = _('Login failed. Please try again.')
            else:
                values['error'] = _('Please fill in all fields.')

        return request.render('eth_agency_portal.agency_login', values)

    @http.route('/agency/logout', type='http', auth="public", website=True, csrf=False)
    def agency_logout(self, **kwargs):
        """Agency logout"""
        try:
            token = request.session.get('agency_token')
            if token:
                auth_service = request.env['agency.auth.service'].sudo()
                auth_service.logout_user(token)

            # Clear session using base method
            self._clear_session()

        except Exception as e:
            _logger.error(f"Logout error: {str(e)}")

        return request.redirect('/agency/login')

    @http.route('/agency/forgot-password', type='http', auth="public", website=True, csrf=False)
    @auto_language
    def agency_forgot_password(self, **kwargs):
        """Forgot password page for portal users"""
        # Prepare values dictionary
        values = {
            'current_language': LanguageManager.get_current_language(),
            'available_languages': LanguageManager.get_available_languages(),
        }

        # Handle forgot password form submission
        if request.httprequest.method == 'POST':
            email = kwargs.get('email', '').strip()

            if not email:
                values['error'] = _('Please enter your email address.')
            elif '@' not in email:
                values['error'] = _('Please enter a valid email address.')
            else:
                try:
                    # Use agency auth service to send reset email
                    auth_service = request.env['agency.auth.service'].sudo()
                    result = auth_service.send_password_reset_email(email)

                    if result['success']:
                        values['success'] = _('Password reset instructions have been sent to your email address.')
                        values['email_sent'] = True
                    else:
                        values['error'] = result['message']

                except Exception as e:
                    _logger.error(f"Forgot password error: {str(e)}")
                    values['error'] = _('Failed to send reset email. Please try again.')

        return request.render('eth_agency_portal.agency_forgot_password', values)

    @http.route('/agency/reset-password', type='http', auth="public", website=True, csrf=False)
    @auto_language
    def agency_reset_password(self, token=None, **kwargs):
        """Reset password page for portal users"""
        # Prepare values dictionary
        values = {
            'token': token,
            'current_language': LanguageManager.get_current_language(),
            'available_languages': LanguageManager.get_available_languages(),
        }

        # Check if token is provided
        if not token:
            values['error'] = _('Invalid or missing reset token.')
            return request.render('eth_agency_portal.agency_reset_password', values)

        # Validate token first
        try:
            auth_service = request.env['agency.auth.service'].sudo()
            token_validation = auth_service.validate_reset_token(token)

            if not token_validation['success']:
                values['error'] = token_validation['message']
                return request.render('eth_agency_portal.agency_reset_password', values)

            values['user_email'] = token_validation.get('user_email', '')

        except Exception as e:
            _logger.error(f"Token validation error: {str(e)}")
            values['error'] = _('Invalid or expired reset token.')
            return request.render('eth_agency_portal.agency_reset_password', values)

        # Handle password reset form submission
        if request.httprequest.method == 'POST':
            new_password = kwargs.get('new_password', '')
            confirm_password = kwargs.get('confirm_password', '')

            if not new_password or not confirm_password:
                values['error'] = _('All fields are required.')
            elif new_password != confirm_password:
                values['error'] = _('Passwords do not match.')
            elif len(new_password) < 6:
                values['error'] = _('Password must be at least 6 characters long.')
            else:
                try:
                    # Reset password using auth service
                    auth_service = request.env['agency.auth.service'].sudo()
                    result = auth_service.reset_password_with_token(token, new_password)

                    if result['success']:
                        # Redirect to login with success message
                        return request.redirect('/agency/login?password_reset=success')
                    else:
                        values['error'] = result['message']

                except Exception as e:
                    _logger.error(f"Reset password error: {str(e)}")
                    values['error'] = _('Failed to reset password. Please try again.')

        return request.render('eth_agency_portal.agency_reset_password', values)
