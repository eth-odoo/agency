# -*- coding: utf-8 -*-
"""
Main Portal Controller - Login, Dashboard, Navigation
"""
import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class PortalMain(http.Controller):
    """Main portal controller for login and dashboard"""

    def _get_agency_token(self):
        """Get agency token from session"""
        return request.session.get('agency_token')

    def _get_agency_user(self):
        """Get current agency user from session"""
        user_id = request.session.get('agency_user_id')
        if user_id:
            return request.env['agency.user'].sudo().browse(user_id)
        return None

    def _check_login(self):
        """Check if user is logged in"""
        token = self._get_agency_token()
        _logger.info(f"_check_login: token from session: {bool(token)}")

        if not token:
            _logger.info("_check_login: No token in session, returning False")
            return False

        # Validate token
        auth_service = request.env['agency.auth.service'].sudo()
        result = auth_service.validate_token(token)
        _logger.info(f"_check_login: Token validation result: {result.get('success')}")
        return result.get('success', False)

    def _portal_context(self, **extra):
        """Get common portal context"""
        user = self._get_agency_user()
        agency = user.agency_id if user else None

        ctx = {
            'agency_user': user,
            'agency': agency,
            'is_logged_in': bool(user and agency),
        }
        ctx.update(extra)
        return ctx

    # ==================== Login/Logout ====================

    @http.route('/agency', type='http', auth='public', website=True)
    def portal_home(self, **kwargs):
        """Portal home - redirect to dashboard or login"""
        if self._check_login():
            return request.redirect('/agency/dashboard')
        return request.redirect('/agency/login')

    @http.route('/agency/login', type='http', auth='public', website=True, methods=['GET'])
    def portal_login(self, **kwargs):
        """Portal login page"""
        _logger.info("portal_login GET handler called")
        if self._check_login():
            return request.redirect('/agency/dashboard')

        error = kwargs.get('error')
        message = kwargs.get('message')
        return request.render('eth_agency_portal.portal_login', {
            'error': error,
            'message': message,
        })

    @http.route('/agency/login/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_login_submit(self, **kwargs):
        """Handle login form submission"""
        email = kwargs.get('email', '').strip()
        password = kwargs.get('password', '')

        _logger.info(f"Login attempt for email: {email}")

        if not email or not password:
            _logger.warning(f"Missing credentials - email: {bool(email)}, password: {bool(password)}")
            return request.redirect('/agency/login?error=missing_credentials')

        # Authenticate via local auth service
        auth_service = request.env['agency.auth.service'].sudo()
        result = auth_service.authenticate_user(email, password)

        _logger.info(f"Auth result for {email}: success={result.get('success')}, message={result.get('message')}")

        if result.get('success'):
            # Store session data
            token = result.get('token')
            user_id = result.get('user_id')
            agency_id = result.get('user_data', {}).get('agency_id')

            _logger.info(f"Storing session - token: {bool(token)}, user_id: {user_id}, agency_id: {agency_id}")

            request.session['agency_token'] = token
            request.session['agency_user_id'] = user_id
            request.session['agency_id'] = agency_id

            # Force session save
            request.session.modified = True

            _logger.info(f"Agency user logged in successfully: {email}")
            return request.redirect('/agency/dashboard')
        else:
            _logger.warning(f"Failed login attempt for {email}: {result.get('message')}")
            return request.redirect('/agency/login?error=invalid_credentials')

    @http.route('/agency/logout', type='http', auth='public', website=True)
    def portal_logout(self, **kwargs):
        """Logout and clear session"""
        token = self._get_agency_token()

        if token:
            auth_service = request.env['agency.auth.service'].sudo()
            auth_service.logout_user(token)

        # Clear session
        request.session.pop('agency_token', None)
        request.session.pop('agency_user_id', None)
        request.session.pop('agency_id', None)

        return request.redirect('/agency/login')

    # ==================== Dashboard ====================

    @http.route('/agency/dashboard', type='http', auth='public', website=True)
    def portal_dashboard(self, **kwargs):
        """Portal dashboard"""
        if not self._check_login():
            return request.redirect('/agency/login')

        user = self._get_agency_user()
        agency = user.agency_id if user else None

        # Get wallet from Travel API if configured
        wallet_data = {'balance': 0, 'currency': 'EUR'}
        api_client = request.env['travel.api.client'].sudo()
        config = api_client._get_api_config()

        if config.get('base_url'):
            token = self._get_agency_token()
            result = api_client.get_bonus_wallet(token)
            if result.get('success') and result.get('data'):
                wallet_data = result['data']

        context = self._portal_context(
            wallet=wallet_data,
        )

        return request.render('eth_agency_portal.portal_dashboard', context)

    # ==================== Debug (remove in production) ====================

    @http.route('/agency/debug/users', type='http', auth='public', website=True)
    def debug_users(self, **kwargs):
        """Debug endpoint to check agency users - REMOVE IN PRODUCTION"""
        users = request.env['agency.user'].sudo().search([])
        html = "<h2>Agency Users Debug</h2><table border='1' style='border-collapse: collapse;'>"
        html += "<tr><th>ID</th><th>Name</th><th>Email</th><th>Active</th><th>Has Password</th><th>Agency</th></tr>"
        for user in users:
            html += f"<tr><td>{user.id}</td><td>{user.name}</td><td>{user.email}</td>"
            html += f"<td>{user.active}</td><td>{bool(user.password_hash)}</td>"
            html += f"<td>{user.agency_id.name if user.agency_id else 'N/A'}</td></tr>"
        html += "</table>"

        # Also show registrations
        registrations = request.env['agency.registration'].sudo().search([])
        html += "<h2>Registrations</h2><table border='1' style='border-collapse: collapse;'>"
        html += "<tr><th>ID</th><th>Name</th><th>Agency Name</th><th>Email</th><th>State</th><th>Agency User</th></tr>"
        for reg in registrations:
            html += f"<tr><td>{reg.id}</td><td>{reg.name}</td><td>{reg.agency_name}</td>"
            html += f"<td>{reg.authorized_email}</td><td>{reg.state}</td>"
            html += f"<td>{reg.agency_user_id.id if reg.agency_user_id else 'N/A'}</td></tr>"
        html += "</table>"

        return html

    @http.route('/agency/debug/test-login', type='http', auth='public', website=True)
    def debug_test_login(self, email=None, password=None, **kwargs):
        """Debug endpoint to test login - REMOVE IN PRODUCTION"""
        if not email or not password:
            return """
            <h2>Test Login</h2>
            <form method='get'>
                <label>Email: <input type='text' name='email'/></label><br/>
                <label>Password: <input type='text' name='password'/></label><br/>
                <button type='submit'>Test</button>
            </form>
            """

        auth_service = request.env['agency.auth.service'].sudo()
        result = auth_service.authenticate_user(email, password)

        html = f"<h2>Login Test Result</h2>"
        html += f"<p><strong>Email:</strong> {email}</p>"
        html += f"<p><strong>Password:</strong> {password}</p>"
        html += f"<p><strong>Success:</strong> {result.get('success')}</p>"
        html += f"<p><strong>Message:</strong> {result.get('message', 'N/A')}</p>"
        html += f"<p><strong>Token:</strong> {bool(result.get('token'))}</p>"
        html += f"<p><strong>User ID:</strong> {result.get('user_id', 'N/A')}</p>"

        return html

    # ==================== Forgot Password ====================

    @http.route('/agency/forgot-password', type='http', auth='public', website=True, methods=['GET'])
    def portal_forgot_password(self, **kwargs):
        """Forgot password page"""
        return request.render('eth_agency_portal.portal_forgot_password', {
            'success': kwargs.get('success'),
            'error': kwargs.get('error'),
        })

    @http.route('/agency/forgot-password/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_forgot_password_submit(self, **kwargs):
        """Handle forgot password submission"""
        email = kwargs.get('email', '').strip()

        if not email:
            return request.redirect('/agency/forgot-password?error=missing_email')

        auth_service = request.env['agency.auth.service'].sudo()
        result = auth_service.request_password_reset(email)

        if result.get('success'):
            return request.redirect('/agency/forgot-password?success=1')
        else:
            return request.redirect('/agency/forgot-password?error=failed')

    @http.route('/agency/reset-password/<string:token>', type='http', auth='public', website=True, methods=['GET'])
    def portal_reset_password(self, token, **kwargs):
        """Reset password page"""
        # Validate reset token
        auth_service = request.env['agency.auth.service'].sudo()
        result = auth_service.validate_reset_token(token)

        if not result.get('success'):
            return request.render('eth_agency_portal.portal_reset_password_invalid')

        return request.render('eth_agency_portal.portal_reset_password', {
            'token': token,
            'error': kwargs.get('error'),
        })

    @http.route('/agency/reset-password/<string:token>/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_reset_password_submit(self, token, **kwargs):
        """Handle password reset submission"""
        password = kwargs.get('password', '')
        confirm_password = kwargs.get('confirm_password', '')

        if not password or len(password) < 8:
            return request.redirect(f'/agency/reset-password/{token}?error=invalid_password')

        if password != confirm_password:
            return request.redirect(f'/agency/reset-password/{token}?error=password_mismatch')

        auth_service = request.env['agency.auth.service'].sudo()
        result = auth_service.reset_password(token, password)

        if result.get('success'):
            return request.redirect('/agency/login?message=password_reset')
        else:
            return request.redirect(f'/agency/reset-password/{token}?error=failed')
