# -*- coding: utf-8 -*-
import hashlib
import secrets
from datetime import datetime, timedelta
from odoo import models, fields, api, exceptions, _


class AgencyUser(models.Model):
    _name = 'agency.user'
    _description = 'Agency User'
    _inherit = ['mail.thread']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char('Full Name', required=True, tracking=True)
    email = fields.Char('Email', required=True, tracking=True)
    phone = fields.Char('Phone', tracking=True)
    agency_id = fields.Many2one(
        'travel.agency', 'Agency', required=True, ondelete='cascade', tracking=True
    )
    is_master = fields.Boolean('Is Master User', default=False, tracking=True)
    active = fields.Boolean('Active', default=True, tracking=True)

    # Location fields
    country_id = fields.Many2one('res.country', 'Country', tracking=True)
    city_id = fields.Many2one('res.country.state', 'City', tracking=True)
    address = fields.Text('Address', tracking=True)

    # Authentication fields
    password_hash = fields.Char('Password Hash')
    last_login = fields.Datetime('Last Login')
    login_token = fields.Char('Login Token')
    token_expiry = fields.Datetime('Token Expiry')

    # Password Reset Fields
    password_reset_token = fields.Char(
        string='Password Reset Token',
        help='Token used for password reset'
    )
    password_reset_expiry = fields.Datetime(
        string='Password Reset Expiry',
        help='Expiry date and time for password reset token'
    )

    # Permissions
    can_create_users = fields.Boolean('Can Create Users', default=False, tracking=True)
    can_manage_bookings = fields.Boolean('Can Manage Bookings', default=True, tracking=True)
    can_view_reports = fields.Boolean('Can View Reports', default=False, tracking=True)
    can_manage_agency = fields.Boolean('Can Manage Agency', default=False, tracking=True)

    # Audit fields
    created_by_user_id = fields.Many2one('agency.user', 'Created By')
    created_date = fields.Datetime('Created Date', default=fields.Datetime.now)
    last_updated_by_user_id = fields.Many2one('agency.user', 'Last Updated By')
    last_updated_date = fields.Datetime('Last Updated Date')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set master user permissions"""
        for vals in vals_list:
            if vals.get('is_master'):
                vals.update({
                    'can_create_users': True,
                    'can_manage_bookings': True,
                    'can_view_reports': True,
                    'can_manage_agency': True,
                })
        return super(AgencyUser, self).create(vals_list)

    def write(self, vals):
        """Override write to update last_updated fields"""
        vals['last_updated_date'] = fields.Datetime.now()
        return super(AgencyUser, self).write(vals)

    @api.constrains('email', 'agency_id')
    def _check_unique_email_per_agency(self):
        """Check email uniqueness per agency"""
        for record in self:
            if record.email:
                domain = [
                    ('email', '=', record.email),
                    ('agency_id', '=', record.agency_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(
                        _('Email must be unique per agency!')
                    )

    @api.constrains('is_master', 'agency_id')
    def _check_single_master_per_agency(self):
        """Ensure only one master user per agency"""
        for record in self:
            if record.is_master:
                domain = [
                    ('is_master', '=', True),
                    ('agency_id', '=', record.agency_id.id),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(
                        _('Only one master user allowed per agency!')
                    )

    def set_password(self, password):
        """Set password hash"""
        if not password:
            raise exceptions.ValidationError(_('Password cannot be empty!'))

        # Generate salt and hash
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        self.password_hash = salt + ':' + password_hash.hex()

    def check_password(self, password):
        """Check if password is correct"""
        import logging
        _logger = logging.getLogger(__name__)

        if not self.password_hash or not password:
            _logger.warning(f"check_password: Missing hash or password - hash: {bool(self.password_hash)}, password: {bool(password)}")
            return False

        try:
            salt, stored_hash = self.password_hash.split(':')
            password_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            computed_hash = password_hash.hex()
            result = stored_hash == computed_hash

            if not result:
                _logger.warning(f"check_password: Hash mismatch for user {self.email}")
                _logger.debug(f"check_password: stored_hash length: {len(stored_hash)}, computed_hash length: {len(computed_hash)}")

            return result
        except Exception as e:
            _logger.error(f"check_password: Exception - {str(e)}")
            return False

    def generate_login_token(self):
        """Generate login token"""
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(hours=24)

        self.write({
            'login_token': token,
            'token_expiry': expiry,
            'last_login': fields.Datetime.now()
        })
        return token

    def validate_token(self, token):
        """Validate login token"""
        if not token or not self.login_token or not self.token_expiry:
            return False

        if self.login_token != token:
            return False

        if datetime.now() > self.token_expiry:
            self.write({
                'login_token': False,
                'token_expiry': False
            })
            return False

        return True

    def invalidate_token(self):
        """Invalidate current token (logout)"""
        self.write({
            'login_token': False,
            'token_expiry': False
        })

    def get_permissions(self):
        """Get user permissions as dictionary"""
        return {
            'can_create_users': self.can_create_users,
            'can_manage_bookings': self.can_manage_bookings,
            'can_view_reports': self.can_view_reports,
            'can_manage_agency': self.can_manage_agency,
            'is_master': self.is_master
        }

    def name_get(self):
        """Custom name_get to show name and email"""
        result = []
        for record in self:
            name = f"{record.name} ({record.email})"
            result.append((record.id, name))
        return result
