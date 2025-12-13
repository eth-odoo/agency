# -*- coding: utf-8 -*-
import logging
import random
import string
import json
from odoo import http, _
from odoo.http import request
from werkzeug.wrappers import Response
from .base import AgencyPortalBase, require_auth, auto_language

_logger = logging.getLogger(__name__)


class UserManagementController(AgencyPortalBase):
    """User management controllers"""

    def _generate_random_password(self, length=12):
        """Generate a random secure password"""
        characters = string.ascii_letters + string.digits
        password = ''.join(random.choice(characters) for i in range(length))
        # Ensure at least one of each type
        if not any(c.isupper() for c in password):
            password = password[:-1] + random.choice(string.ascii_uppercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + random.choice(string.digits)
        return password

    def _json_response(self, data):
        """Helper method to return JSON response"""
        return Response(
            json.dumps(data),
            content_type='application/json',
            status=200
        )

    @http.route('/agency/users', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_users(self, **kwargs):
        """Agency users management page"""
        try:
            # Check permission
            if not self._has_permission('can_create_users'):
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='users',
                        message=_('You do not have permission to manage users.')
                    ))

            # Get agency users
            try:
                token = request.session.get('agency_token')
                auth_service = request.env['agency.auth.service'].sudo()
                result = auth_service.get_agency_users(token)
                users = result['users'] if result['success'] else []
            except Exception as e:
                _logger.error(f"Error getting agency users: {str(e)}")
                users = []

            values = self._prepare_values(
                page_name='users',
                users=users,
            )

            return request.render('eth_agency_portal.agency_users', values)

        except Exception as e:
            _logger.error(f"Error in users page: {str(e)}")
            return request.redirect('/agency/dashboard')

    @http.route('/agency/users/create', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_user_create(self, **kwargs):
        """Create new agency user - AUTO PASSWORD GENERATION"""
        try:
            # Check permission
            if not self._has_permission('can_create_users'):
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='users',
                        message=_('You do not have permission to create users.')
                    ))

            # Get countries for dropdown
            countries = request.env['res.country'].sudo().search([])

            values = self._prepare_values(
                page_name='users',
                countries=countries
            )

            # Handle form submission
            if request.httprequest.method == 'POST':
                try:
                    # GENERATE AUTO PASSWORD
                    auto_password = self._generate_random_password()

                    new_user_data = {
                        'name': kwargs.get('name', '').strip(),
                        'email': kwargs.get('email', '').strip(),
                        'phone': kwargs.get('phone', '').strip(),
                        'password': auto_password,
                        'country_id': kwargs.get('country_id', ''),
                        'city_id': kwargs.get('city_id', ''),
                        'address': kwargs.get('address', '').strip(),
                        'can_create_users': bool(kwargs.get('can_create_users')),
                        'can_manage_bookings': bool(kwargs.get('can_manage_bookings')),
                        'can_view_reports': bool(kwargs.get('can_view_reports')),
                        'can_manage_agency': bool(kwargs.get('can_manage_agency')),
                    }

                    # Validate required fields
                    if not all([new_user_data['name'], new_user_data['email']]):
                        values['error'] = _('Name and email are required.')
                    else:
                        # Create user
                        token = request.session.get('agency_token')
                        auth_service = request.env['agency.auth.service'].sudo()
                        result = auth_service.create_agency_user(new_user_data, token)

                        if result['success']:
                            user_id = result.get('user_id')
                            if user_id:
                                request.session[f'temp_password_{user_id}'] = auto_password

                            values['success'] = _('User created successfully!')
                            return request.redirect('/agency/users')
                        else:
                            values['error'] = result['message']

                except Exception as e:
                    _logger.error(f"Error creating user: {str(e)}")
                    values['error'] = _('Failed to create user. Please try again.')

            return request.render('eth_agency_portal.agency_user_create', values)

        except Exception as e:
            _logger.error(f"Error in create user page: {str(e)}")
            return request.redirect('/agency/users')

    @http.route('/agency/users/edit/<int:user_id>', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_user_edit(self, user_id, **kwargs):
        """Edit agency user"""
        try:
            # Check permission
            if not self._has_permission('can_create_users'):
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='users',
                        message=_('You do not have permission to edit users.')
                    ))

            # Get user to edit
            try:
                token = request.session.get('agency_token')
                auth_service = request.env['agency.auth.service'].sudo()
                result = auth_service.get_agency_users(token)

                if result['success']:
                    user_to_edit = next((u for u in result['users'] if u['id'] == user_id), None)
                    if not user_to_edit:
                        return request.redirect('/agency/users')
                else:
                    return request.redirect('/agency/users')
            except Exception as e:
                _logger.error(f"Error getting user: {str(e)}")
                return request.redirect('/agency/users')

            # Get countries for dropdown
            countries = request.env['res.country'].sudo().search([])

            # Get cities for selected country
            cities = []
            if user_to_edit.get('country_id'):
                cities = request.env['res.country.state'].sudo().search([
                    ('country_id', '=', user_to_edit['country_id'][0])
                ])

            values = self._prepare_values(
                page_name='users',
                user_to_edit=user_to_edit,
                countries=countries,
                cities=cities
            )

            # Handle form submission
            if request.httprequest.method == 'POST':
                try:
                    update_data = {
                        'name': kwargs.get('name', '').strip(),
                        'email': kwargs.get('email', '').strip(),
                        'phone': kwargs.get('phone', '').strip(),
                        'country_id': kwargs.get('country_id', ''),
                        'city_id': kwargs.get('city_id', ''),
                        'address': kwargs.get('address', '').strip(),
                        'can_create_users': bool(kwargs.get('can_create_users')),
                        'can_manage_bookings': bool(kwargs.get('can_manage_bookings')),
                        'can_view_reports': bool(kwargs.get('can_view_reports')),
                        'can_manage_agency': bool(kwargs.get('can_manage_agency')),
                    }

                    # Update user
                    result = auth_service.update_agency_user(user_id, update_data, token)

                    if result['success']:
                        return request.redirect('/agency/users')
                    else:
                        values['error'] = result['message']

                except Exception as e:
                    _logger.error(f"Error updating user: {str(e)}")
                    values['error'] = _('Failed to update user. Please try again.')

            return request.render('eth_agency_portal.agency_user_edit', values)

        except Exception as e:
            _logger.error(f"Error in edit user page: {str(e)}")
            return request.redirect('/agency/users')

    @http.route('/agency/users/delete/<int:user_id>', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    def agency_user_delete(self, user_id, **kwargs):
        """Delete agency user"""
        try:
            # Check permission
            if not self._has_permission('can_create_users'):
                return request.redirect('/agency/users')

            token = request.session.get('agency_token')
            auth_service = request.env['agency.auth.service'].sudo()
            auth_service.delete_agency_user(user_id, token)

        except Exception as e:
            _logger.error(f"Error deleting user: {str(e)}")

        return request.redirect('/agency/users')

    @http.route('/agency/users/send_credentials/<int:user_id>', type='http', auth="public", methods=['POST'], csrf=False)
    @require_auth()
    def send_user_credentials(self, user_id, **kwargs):
        """Send login credentials to user via email"""
        try:
            token = request.session.get('agency_token')
            auth_service = request.env['agency.auth.service'].sudo()
            result = auth_service.get_agency_users(token)

            if not result['success']:
                return self._json_response({'success': False, 'message': 'Failed to get user information'})

            user = next((u for u in result['users'] if u['id'] == user_id), None)
            if not user:
                return self._json_response({'success': False, 'message': 'User not found'})

            if not user.get('email'):
                return self._json_response({'success': False, 'message': 'User has no email address'})

            # Get password (from session or generate new one)
            password = request.session.get(f'temp_password_{user_id}')
            if not password:
                password = self._generate_random_password()
                update_result = auth_service.update_agency_user(user_id, {'password': password}, token)
                if not update_result.get('success'):
                    return self._json_response({'success': False, 'message': 'Failed to generate new password'})

            # Prepare email content
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            login_url = f"{base_url}/agency/login"

            email_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0;">Welcome!</h1>
                </div>

                <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
                    <h2 style="color: #2c3e50; margin-top: 0;">Dear {user.get('name')},</h2>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Your Agency Portal account has been created. Below are your login credentials:
                    </p>

                    <div style="background-color: #f8f9fa; padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #667eea;">
                        <p style="margin: 10px 0; color: #333;">
                            <strong style="display: inline-block; width: 120px;">Login URL:</strong>
                            <a href="{login_url}" style="color: #667eea; text-decoration: none;">{login_url}</a>
                        </p>
                        <p style="margin: 10px 0; color: #333;">
                            <strong style="display: inline-block; width: 120px;">Username:</strong>
                            <span style="color: #667eea;">{user.get('email')}</span>
                        </p>
                        <p style="margin: 10px 0; color: #333;">
                            <strong style="display: inline-block; width: 120px;">Password:</strong>
                            <code style="background-color: #2c3e50; color: #fff; padding: 8px 15px; border-radius: 4px;">{password}</code>
                        </p>
                    </div>

                    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <p style="margin: 0; color: #856404;">
                            <strong>Important:</strong> Please change your password after first login.
                        </p>
                    </div>

                    <p style="color: #555; font-size: 14px; margin-top: 20px;">
                        Best regards,<br/>
                        <strong>Agency Management Team</strong>
                    </p>
                </div>
            </div>
            """

            # Send email
            mail_values = {
                'subject': f'Agency Portal - Your Login Credentials',
                'body_html': email_body,
                'email_to': user.get('email'),
                'email_from': request.env.user.email or 'noreply@agency.com',
                'auto_delete': False,
            }

            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()

            # Clear temp password after sending
            if f'temp_password_{user_id}' in request.session:
                del request.session[f'temp_password_{user_id}']

            return self._json_response({
                'success': True,
                'message': f'Login credentials sent to {user.get("email")} successfully'
            })

        except Exception as e:
            _logger.error(f"Error sending credentials: {str(e)}")
            return self._json_response({
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            })

    @http.route('/agency/users/reset_password/<int:user_id>', type='http', auth="public", methods=['POST'], csrf=False)
    @require_auth()
    def reset_user_password(self, user_id, **kwargs):
        """Reset password and send to user via email"""
        try:
            token = request.session.get('agency_token')
            auth_service = request.env['agency.auth.service'].sudo()
            result = auth_service.get_agency_users(token)

            if not result['success']:
                return self._json_response({'success': False, 'message': 'Failed to get user information'})

            user = next((u for u in result['users'] if u['id'] == user_id), None)
            if not user:
                return self._json_response({'success': False, 'message': 'User not found'})

            if not user.get('email'):
                return self._json_response({'success': False, 'message': 'User has no email address'})

            # Generate new password
            new_password = self._generate_random_password()

            # Update user password
            update_result = auth_service.update_agency_user(user_id, {'password': new_password}, token)
            if not update_result.get('success'):
                return self._json_response({'success': False, 'message': 'Failed to reset password'})

            # Prepare email content
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            login_url = f"{base_url}/agency/login"

            email_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0;">Password Reset</h1>
                </div>

                <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
                    <h2 style="color: #2c3e50; margin-top: 0;">Dear {user.get('name')},</h2>
                    <p style="color: #555; font-size: 16px; line-height: 1.6;">
                        Your password has been reset. Below are your new login credentials:
                    </p>

                    <div style="background-color: #f8f9fa; padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #f5576c;">
                        <p style="margin: 10px 0; color: #333;">
                            <strong style="display: inline-block; width: 120px;">Login URL:</strong>
                            <a href="{login_url}" style="color: #f5576c; text-decoration: none;">{login_url}</a>
                        </p>
                        <p style="margin: 10px 0; color: #333;">
                            <strong style="display: inline-block; width: 120px;">Username:</strong>
                            <span style="color: #f5576c;">{user.get('email')}</span>
                        </p>
                        <p style="margin: 10px 0; color: #333;">
                            <strong style="display: inline-block; width: 120px;">New Password:</strong>
                            <code style="background-color: #2c3e50; color: #fff; padding: 8px 15px; border-radius: 4px;">{new_password}</code>
                        </p>
                    </div>

                    <p style="color: #555; font-size: 14px; margin-top: 20px;">
                        Best regards,<br/>
                        <strong>Agency Management Team</strong>
                    </p>
                </div>
            </div>
            """

            # Send email
            mail_values = {
                'subject': f'Agency Portal - Password Reset',
                'body_html': email_body,
                'email_to': user.get('email'),
                'email_from': request.env.user.email or 'noreply@agency.com',
                'auto_delete': False,
            }

            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.send()

            return self._json_response({
                'success': True,
                'message': f'Password reset and sent to {user.get("email")} successfully'
            })

        except Exception as e:
            _logger.error(f"Error resetting password: {str(e)}")
            return self._json_response({
                'success': False,
                'message': f'Failed to reset password: {str(e)}'
            })

    @http.route('/agency/get_cities/<int:country_id>', type='json', auth="public", methods=['POST'], csrf=False)
    def get_cities(self, country_id, **kwargs):
        """Get cities for a country - AJAX endpoint"""
        try:
            cities = request.env['res.country.state'].sudo().search([
                ('country_id', '=', country_id)
            ])
            return {
                'cities': [{'id': city.id, 'name': city.name} for city in cities]
            }
        except Exception as e:
            _logger.error(f"Error getting cities: {str(e)}")
            return {'cities': []}
