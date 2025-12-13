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
                _logger.warning(f"Auth: Missing email or password")
                return {'success': False, 'message': 'Email and password are required'}

            search_email = email.lower().strip()
            _logger.info(f"Auth: Searching for user with email: {search_email}")

            user = self.env['agency.user'].search([
                ('email', '=', search_email),
                ('active', '=', True)
            ], limit=1)

            if not user:
                # Debug: check if user exists with different case or inactive
                all_users = self.env['agency.user'].search([])
                _logger.warning(f"Auth: User not found for email: {search_email}")
                _logger.info(f"Auth: All users in system: {[(u.id, u.email, u.active) for u in all_users]}")
                return {'success': False, 'message': 'Invalid email or password'}

            _logger.info(f"Auth: Found user {user.id} - {user.name} ({user.email})")
            _logger.info(f"Auth: User has password_hash: {bool(user.password_hash)}")

            if not user.check_password(password):
                _logger.warning(f"Auth: Password check failed for user: {user.email}")
                _logger.info(f"Auth: Password hash length: {len(user.password_hash) if user.password_hash else 0}")
                return {'success': False, 'message': 'Invalid email or password'}

            token = user.generate_login_token()
            _logger.info(f"Auth: Generated token for user {user.email}: {bool(token)}")

            return {
                'success': True,
                'token': token,
                'user_id': user.id,
                'user_data': self._get_user_data(user)
            }

        except Exception as e:
            _logger.error(f"Auth: Exception during authentication: {str(e)}", exc_info=True)
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
            reset_url = f"{base_url}/agency/reset-password/{reset_token}"

            self._send_reset_email(user, reset_url)

            return {'success': True, 'message': 'Reset instructions sent to your email.'}

        except Exception as e:
            _logger.error(f"Password reset error: {str(e)}")
            return {'success': False, 'message': 'Failed to send reset email.'}

    def request_password_reset(self, email):
        """Alias for send_password_reset_email - used by portal controller"""
        return self.send_password_reset_email(email)

    def _send_reset_email(self, user, reset_url):
        """Send password reset email"""
        subject = "Password Reset - Agency Portal"
        body_html = f"""
        <div style="margin: 0px; padding: 0px; font-family: Arial, sans-serif;">
            <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family: Arial, sans-serif; color: #454748; width: 100%; border-collapse: separate;">
                <tr>
                    <td align="center">
                        <table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 24px; background-color: white; border: 1px solid #e7e7e7; border-collapse: separate;">
                            <tr>
                                <td align="center" style="min-width: 590px;">
                                    <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse: separate;">
                                        <tr>
                                            <td valign="middle">
                                                <span style="font-size: 10px;">Password Reset</span><br/>
                                                <span style="font-size: 20px; font-weight: bold; color: #dc3545;">SECURITY</span>
                                            </td>
                                            <td valign="middle" align="right">
                                                <span style="font-size: 24px; font-weight: bold; color: #667eea;">Agency Portal</span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td colspan="2" style="text-align: center;">
                                                <hr width="100%" style="background-color: #e7e7e7; border: medium none; clear: both; display: block; font-size: 0px; min-height: 1px; line-height: 0; margin: 16px 0px 16px 0px;"/>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="min-width: 590px;">
                                    <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse: separate;">
                                        <tr>
                                            <td valign="top" style="font-size: 13px;">
                                                <div>
                                                    <p>Dear {user.name},</p>

                                                    <p>You have requested to reset your password for the <strong>Agency Portal</strong>.</p>

                                                    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                                                        <p><strong>Security Notice:</strong></p>
                                                        <p style="margin: 5px 0;">This password reset link is valid for only 24 hours.</p>
                                                        <p style="margin: 5px 0;">If you did not request this, please ignore this email.</p>
                                                    </div>

                                                    <div style="text-align: center; margin: 25px 0;">
                                                        <p style="margin-bottom: 15px; font-weight: bold;">Click the button below to reset your password:</p>
                                                        <a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                                                            Reset Password
                                                        </a>
                                                    </div>

                                                    <p style="font-size: 12px; color: #6c757d; margin: 20px 0;">
                                                        <strong>Link not working?</strong> Copy and paste this URL into your browser:<br/>
                                                        <span style="background-color: #f8f9fa; padding: 5px; border: 1px solid #dee2e6; word-break: break-all; display: inline-block; margin-top: 8px;">
                                                            {reset_url}
                                                        </span>
                                                    </p>

                                                    <div style="background-color: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin: 20px 0;">
                                                        <p><strong>After Password Reset:</strong></p>
                                                        <ol style="margin: 10px 0; padding-left: 20px;">
                                                            <li>Choose a strong password (at least 8 characters)</li>
                                                            <li>Log in to the Agency Portal</li>
                                                            <li>Continue using the portal</li>
                                                        </ol>
                                                    </div>

                                                    <p>Best regards,<br/>
                                                    <strong>Agency Support Team</strong></p>
                                                </div>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" style="min-width: 590px;">
                                    <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: #f8f9fa; padding: 0px 8px 0px 8px; border-collapse: separate;">
                                        <tr>
                                            <td valign="middle" style="font-size: 10px; text-align: center; padding: 15px;">
                                                <p style="margin: 0; color: #6c757d;">This email was sent for security purposes.</p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
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

    def reset_password(self, token, new_password):
        """Alias for reset_password_with_token - used by portal controller"""
        return self.reset_password_with_token(token, new_password)

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

    def change_user_password(self, token, current_password, new_password):
        """Change password for authenticated user"""
        try:
            # Validate token
            token_result = self.validate_token(token)
            if not token_result['success']:
                return token_result

            # Get user
            user = self.env['agency.user'].sudo().browse(token_result['user_id'])

            # Check current password
            if not user.check_password(current_password):
                return {
                    'success': False,
                    'message': 'Current password is incorrect.'
                }

            # Set new password
            user.set_password(new_password)

            return {
                'success': True,
                'message': 'Password changed successfully.'
            }

        except Exception as e:
            _logger.error(f"Failed to change password: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to change password. Please try again.'
            }

    def update_agency_user(self, user_id, user_data, current_user_token):
        """Update agency user"""
        try:
            # Validate current user
            auth_result = self.validate_token(current_user_token)
            if not auth_result['success']:
                return auth_result

            current_user = self.env['agency.user'].browse(auth_result['user_id'])

            # Find user to update
            user_to_update = self.env['agency.user'].search([
                ('id', '=', user_id),
                ('agency_id', '=', current_user.agency_id.id)
            ])

            if not user_to_update:
                return {'success': False, 'message': 'User not found'}

            # Check permissions - users can update their own profile
            if not current_user.can_create_users and user_to_update.id != current_user.id:
                return {'success': False, 'message': 'Permission denied'}

            # Update user data
            update_vals = {}
            if user_data.get('name'):
                update_vals['name'] = user_data['name']
            if user_data.get('email'):
                update_vals['email'] = user_data['email'].lower().strip()
            if user_data.get('phone'):
                update_vals['phone'] = user_data['phone']

            # Update location fields
            if 'country_id' in user_data:
                update_vals['country_id'] = int(user_data['country_id']) if user_data['country_id'] else False
            if 'city_id' in user_data:
                update_vals['city_id'] = int(user_data['city_id']) if user_data['city_id'] else False
            if 'address' in user_data:
                update_vals['address'] = user_data['address']

            # Only users with permission can update permissions
            if current_user.can_create_users:
                permission_fields = ['can_create_users', 'can_manage_bookings',
                                   'can_view_reports', 'can_manage_agency']
                for field in permission_fields:
                    if field in user_data:
                        update_vals[field] = user_data[field]

            user_to_update.write(update_vals)

            # Update password if provided
            if user_data.get('password'):
                user_to_update.set_password(user_data['password'])

            _logger.info(f"Agency user updated: {user_to_update.email} by {current_user.email}")

            return {
                'success': True,
                'message': 'User updated successfully',
                'user_data': self._get_user_data(user_to_update)
            }

        except Exception as e:
            _logger.error(f"User update error: {str(e)}")
            return {'success': False, 'message': 'User update failed'}
