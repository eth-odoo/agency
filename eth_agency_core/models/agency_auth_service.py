# -*- coding: utf-8 -*-
import logging
import uuid
from datetime import datetime, timedelta
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class AgencyAuthService(models.Model):
    _name = 'agency.auth.service'
    _description = 'Agency Authentication Service'

    def authenticate_user(self, email, password):
        """Authenticate agency user"""
        try:
            if not email or not password:
                return {'success': False, 'message': 'Email and password are required'}

            user = self.env['agency.user'].search([
                ('email', '=', email.lower().strip()),
                ('active', '=', True)
            ], limit=1)

            if not user:
                _logger.warning(f"Authentication failed - User not found: {email}")
                return {'success': False, 'message': 'Invalid email or password'}

            if not user.check_password(password):
                _logger.warning(f"Authentication failed - Wrong password: {email}")
                return {'success': False, 'message': 'Invalid email or password'}

            token = user.generate_login_token()
            _logger.info(f"User authenticated successfully: {email}")

            return {
                'success': True,
                'token': token,
                'user_id': user.id,
                'user_data': self._get_user_data(user)
            }

        except Exception as e:
            _logger.error(f"Authentication error: {str(e)}")
            return {'success': False, 'message': 'Authentication failed'}

    def _get_user_data(self, user):
        """Get user data dictionary"""
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'country_id': [user.country_id.id, user.country_id.name] if user.country_id else None,
            'city_id': [user.city_id.id, user.city_id.name] if user.city_id else None,
            'address': user.address,
            'agency_id': user.agency_id.id,
            'agency_name': user.agency_id.name,
            'is_master': user.is_master,
            'permissions': user.get_permissions()
        }

    def validate_token(self, token):
        """Validate authentication token"""
        try:
            if not token:
                return {'success': False, 'message': 'Token is required'}

            user = self.env['agency.user'].search([
                ('login_token', '=', token),
                ('active', '=', True)
            ], limit=1)

            if not user:
                return {'success': False, 'message': 'Invalid token'}

            if not user.validate_token(token):
                return {'success': False, 'message': 'Token expired or invalid'}

            return {
                'success': True,
                'user_id': user.id,
                'user_data': self._get_user_data(user)
            }

        except Exception as e:
            _logger.error(f"Token validation error: {str(e)}")
            return {'success': False, 'message': 'Token validation failed'}

    def logout_user(self, token):
        """Logout user by invalidating token"""
        try:
            if not token:
                return {'success': False, 'message': 'Token is required'}

            user = self.env['agency.user'].search([
                ('login_token', '=', token),
                ('active', '=', True)
            ], limit=1)

            if user:
                user.invalidate_token()
                _logger.info(f"User logged out: {user.email}")

            return {'success': True, 'message': 'Logged out successfully'}

        except Exception as e:
            _logger.error(f"Logout error: {str(e)}")
            return {'success': False, 'message': 'Logout failed'}

    def send_password_reset_email(self, email):
        """Send password reset email to user"""
        try:
            user = self.env['agency.user'].sudo().search([
                ('email', '=', email.lower().strip()),
                ('active', '=', True)
            ], limit=1)

            if not user:
                return {'success': False, 'message': 'No user found with this email address.'}

            # Generate reset token
            reset_token = str(uuid.uuid4())
            expiry_time = datetime.now() + timedelta(hours=24)

            user.write({
                'password_reset_token': reset_token,
                'password_reset_expiry': expiry_time
            })

            # Send email
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            reset_url = f"{base_url}/agency/reset-password?token={reset_token}"

            self._send_reset_email(user, reset_url)

            return {'success': True, 'message': 'Reset instructions sent to your email.'}

        except Exception as e:
            _logger.error(f"Password reset error: {str(e)}")
            return {'success': False, 'message': 'Failed to send reset email.'}

    def _send_reset_email(self, user, reset_url):
        """Send password reset email"""
        subject = "Password Reset - Agency Portal"
        body_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Password Reset Request</h2>
            <p>Dear {user.name},</p>
            <p>You have requested to reset your password.</p>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_url}" style="background-color: #dc3545; color: white;
               padding: 10px 20px; text-decoration: none; border-radius: 5px;">
               Reset Password</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you did not request this, please ignore this email.</p>
        </div>
        """

        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_from': self.env.company.email or 'noreply@agency.com',
            'email_to': user.email,
            'auto_delete': True,
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()

    def validate_reset_token(self, token):
        """Validate password reset token"""
        try:
            user = self.env['agency.user'].sudo().search([
                ('password_reset_token', '=', token),
                ('active', '=', True)
            ], limit=1)

            if not user:
                return {'success': False, 'message': 'Invalid reset token.'}

            if user.password_reset_expiry and user.password_reset_expiry < datetime.now():
                user.write({
                    'password_reset_token': False,
                    'password_reset_expiry': False
                })
                return {'success': False, 'message': 'Reset token has expired.'}

            return {
                'success': True,
                'user_id': user.id,
                'user_email': user.email
            }

        except Exception as e:
            _logger.error(f"Token validation error: {str(e)}")
            return {'success': False, 'message': 'Invalid reset token.'}

    def reset_password_with_token(self, token, new_password):
        """Reset password using reset token"""
        try:
            validation = self.validate_reset_token(token)
            if not validation['success']:
                return validation

            user = self.env['agency.user'].sudo().browse(validation['user_id'])
            user.set_password(new_password)
            user.write({
                'password_reset_token': False,
                'password_reset_expiry': False
            })

            return {'success': True, 'message': 'Password reset successfully.'}

        except Exception as e:
            _logger.error(f"Password reset error: {str(e)}")
            return {'success': False, 'message': 'Failed to reset password.'}

    def create_agency_user(self, user_data, current_user_token):
        """Create new agency user"""
        try:
            auth_result = self.validate_token(current_user_token)
            if not auth_result['success']:
                return auth_result

            current_user = self.env['agency.user'].browse(auth_result['user_id'])

            if not current_user.can_create_users:
                return {'success': False, 'message': 'Permission denied'}

            required_fields = ['name', 'email', 'password']
            for field in required_fields:
                if not user_data.get(field):
                    return {'success': False, 'message': f'{field.title()} is required'}

            new_user_vals = {
                'name': user_data['name'],
                'email': user_data['email'].lower().strip(),
                'phone': user_data.get('phone', ''),
                'agency_id': current_user.agency_id.id,
                'can_create_users': user_data.get('can_create_users', False),
                'can_manage_bookings': user_data.get('can_manage_bookings', True),
                'can_view_reports': user_data.get('can_view_reports', False),
                'can_manage_agency': user_data.get('can_manage_agency', False),
                'created_by_user_id': current_user.id
            }

            if user_data.get('country_id'):
                new_user_vals['country_id'] = int(user_data['country_id'])
            if user_data.get('city_id'):
                new_user_vals['city_id'] = int(user_data['city_id'])
            if user_data.get('address'):
                new_user_vals['address'] = user_data['address']

            new_user = self.env['agency.user'].create(new_user_vals)
            new_user.set_password(user_data['password'])

            return {
                'success': True,
                'message': 'User created successfully',
                'user_id': new_user.id,
                'user_data': self._get_user_data(new_user)
            }

        except Exception as e:
            _logger.error(f"User creation error: {str(e)}")
            return {'success': False, 'message': 'User creation failed'}

    def get_agency_users(self, current_user_token):
        """Get all users for current agency"""
        try:
            auth_result = self.validate_token(current_user_token)
            if not auth_result['success']:
                return auth_result

            current_user = self.env['agency.user'].browse(auth_result['user_id'])

            users = self.env['agency.user'].search([
                ('agency_id', '=', current_user.agency_id.id),
                ('active', '=', True)
            ])

            users_data = [self._get_user_data(user) for user in users]

            return {
                'success': True,
                'users': users_data,
                'total_count': len(users_data)
            }

        except Exception as e:
            _logger.error(f"Get users error: {str(e)}")
            return {'success': False, 'message': 'Failed to get users'}
