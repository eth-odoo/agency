# -*- coding: utf-8 -*-
import logging
import base64
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase, require_auth, auto_language, LanguageManager

_logger = logging.getLogger(__name__)


class SettingsController(AgencyPortalBase):
    """Settings and profile management controllers"""

    @http.route('/agency/settings', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_settings(self, **kwargs):
        """Agency settings page"""
        try:
            agency_id = self._get_agency_id()

            # Get detailed agency info for settings
            agency_extra = {}
            if agency_id:
                try:
                    agency = request.env['travel.agency'].sudo().browse(agency_id)
                    _logger.info(f"Loading settings for agency: {agency.name} (id={agency_id})")

                    # Get interested hotels (if hotel extension module installed)
                    interested_hotels = []
                    all_hotels = []
                    try:
                        # Check if interested_hotel_ids field exists (from eth_agency_hotel_ext)
                        if 'interested_hotel_ids' in agency._fields:
                            interested_hotels = [{
                                'id': hotel.id,
                                'name': hotel.name,
                                'code': hotel.code if hasattr(hotel, 'code') else '',
                                'city': hotel.city_id.name if hasattr(hotel, 'city_id') and hotel.city_id else '',
                            } for hotel in agency.interested_hotel_ids]
                            _logger.info(f"Found {len(interested_hotels)} interested hotels for agency")

                        # Get all available hotels for selection (if hotel model exists)
                        if 'eth.travel.hotel' in request.env:
                            hotels = request.env['eth.travel.hotel'].sudo().search([('status', '=', 'active')])
                            all_hotels = [{
                                'id': hotel.id,
                                'name': hotel.name,
                                'code': hotel.code if hasattr(hotel, 'code') else '',
                                'city': hotel.city_id.name if hasattr(hotel, 'city_id') and hotel.city_id else '',
                            } for hotel in hotels]
                            _logger.info(f"Found {len(all_hotels)} available hotels")
                    except Exception as e:
                        _logger.debug(f"Hotel module not available: {e}")

                    # Get membership purposes
                    membership_purposes = []
                    all_purposes = []
                    try:
                        # Get agency's current membership purposes
                        if agency.membership_purpose_ids:
                            membership_purposes = [{
                                'id': purpose.id,
                                'name': purpose.name,
                            } for purpose in agency.membership_purpose_ids]
                            _logger.info(f"Agency has {len(membership_purposes)} membership purposes")

                        # Get all available membership purposes
                        if 'agency.membership.purpose' in request.env:
                            purposes = request.env['agency.membership.purpose'].sudo().search([('active', '=', True)])
                            all_purposes = [{
                                'id': purpose.id,
                                'name': purpose.name,
                            } for purpose in purposes]
                            _logger.info(f"Found {len(all_purposes)} total membership purposes")
                    except Exception as e:
                        _logger.error(f"Membership purpose error: {e}")
                        import traceback
                        _logger.error(traceback.format_exc())

                    # Get pending requests (if update request model exists - from eth_agency_hotel_ext)
                    pending_requests_count = 0
                    update_request_available = False
                    try:
                        # Try to access the model directly
                        UpdateRequest = request.env['agency.update.request'].sudo()
                        update_request_available = True
                        pending_requests = UpdateRequest.search([
                            ('agency_id', '=', agency_id),
                            ('state', 'in', ['draft', 'pending'])
                        ])
                        pending_requests_count = len(pending_requests)
                        _logger.info(f"Update request feature available, {pending_requests_count} pending requests")
                    except KeyError:
                        _logger.info("agency.update.request model not found in registry")
                        update_request_available = False
                    except Exception as e:
                        _logger.error(f"Error checking update request: {e}")
                        update_request_available = False

                    agency_extra = {
                        'interested_hotels': interested_hotels,
                        'all_hotels': all_hotels,
                        'membership_purposes': membership_purposes,
                        'all_purposes': all_purposes,
                        'has_pending_requests': pending_requests_count > 0,
                        'pending_requests_count': pending_requests_count,
                        'update_request_available': update_request_available,
                    }

                    _logger.info(f"Agency extra data: hotels={len(interested_hotels)}/{len(all_hotels)}, purposes={len(membership_purposes)}/{len(all_purposes)}")

                except Exception as e:
                    _logger.error(f"Error getting detailed agency data: {str(e)}")
                    import traceback
                    _logger.error(traceback.format_exc())
                    agency_extra = {}

            # Prepare values with base agency data
            values = self._prepare_values(page_name='settings')

            # Merge agency_extra into agency_data
            if values.get('agency_data') is None:
                values['agency_data'] = {}

            # Update agency_data with extra information (always merge)
            if isinstance(values['agency_data'], dict):
                values['agency_data'].update(agency_extra)
            else:
                values['agency_data'] = agency_extra

            _logger.info(f"Final agency_data keys: {values['agency_data'].keys() if values['agency_data'] else 'None'}")

            return request.render('eth_agency_portal.agency_settings', values)

        except Exception as e:
            _logger.error(f"Error in settings: {str(e)}")
            return request.redirect('/agency/dashboard')

    @http.route('/agency/settings/update-language', type='json', auth='public', methods=['POST'], csrf=False)
    def update_default_language(self, lang_code=None, **kw):
        """Update agency default language"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': _('Unauthorized')}

            agency_id = self._get_agency_id()
            if not agency_id:
                return {'success': False, 'error': _('No agency associated')}

            # Update agency default language
            agency = request.env['travel.agency'].sudo().browse(agency_id)
            if agency.exists():
                agency.write({'default_language': lang_code})

                # Also update session language
                LanguageManager.set_language(lang_code)

                return {
                    'success': True,
                    'message': _('Default language updated successfully')
                }
            else:
                return {'success': False, 'error': _('Agency not found')}

        except Exception as e:
            _logger.error(f"Error updating default language: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/settings/request-update', type='json', auth='public', methods=['POST'], csrf=False)
    def request_agency_update(self, request_type=None, item_ids=None, reason=None, **kw):
        """Create an update request for agency"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': _('Unauthorized')}

            user_data = self._get_current_user()
            agency_id = self._get_agency_id()

            if not agency_id:
                return {'success': False, 'error': _('No agency associated')}

            # Validate input
            if not request_type:
                return {'success': False, 'error': _('Request type is required')}

            if not item_ids:
                return {'success': False, 'error': _('Please select at least one item')}

            # Check if model exists and create request
            try:
                UpdateRequest = request.env['agency.update.request'].sudo()
            except KeyError:
                return {'success': False, 'error': _('Update request feature not available. Please install eth_agency_hotel_ext module.')}

            # Create the request
            request_vals = {
                'agency_id': agency_id,
                'request_type': request_type,
                'reason': reason or '',
                'state': 'pending',
            }

            # Add hotel or membership IDs based on request type
            if request_type in ['add_hotel', 'remove_hotel']:
                request_vals['hotel_ids'] = [(6, 0, item_ids)]
            elif request_type in ['add_membership', 'remove_membership']:
                request_vals['membership_purpose_ids'] = [(6, 0, item_ids)]
            else:
                return {'success': False, 'error': _('Invalid request type')}

            # Create the request
            update_request = UpdateRequest.create(request_vals)

            # Post message
            update_request.message_post(
                body=_('Request created and submitted by %(user)s via Agency Portal', user=user_data.get("name", "User")),
                subject=_('Request Submitted'),
                message_type='notification'
            )

            _logger.info(f"Agency update request created: {update_request.name}")

            return {
                'success': True,
                'message': _('Your request has been submitted successfully. You will be notified once it is reviewed.'),
                'request_id': update_request.id,
                'request_name': update_request.name,
            }

        except Exception as e:
            _logger.error(f"Error creating agency update request: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/settings/get-requests', type='json', auth='public', methods=['POST'], csrf=False)
    def get_agency_requests(self, **kw):
        """Get agency update requests"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': _('Unauthorized')}

            agency_id = self._get_agency_id()
            if not agency_id:
                return {'success': False, 'error': _('No agency associated')}

            # Check if model exists
            try:
                UpdateRequest = request.env['agency.update.request'].sudo()
            except KeyError:
                return {'success': True, 'requests': []}

            # Get requests
            requests = UpdateRequest.search([
                ('agency_id', '=', agency_id)
            ], order='create_date desc', limit=50)

            requests_data = []
            for req in requests:
                data = {
                    'id': req.id,
                    'name': req.name,
                    'request_type': req.request_type,
                    'request_type_label': dict(req._fields['request_type'].selection).get(req.request_type, req.request_type),
                    'state': req.state,
                    'state_label': dict(req._fields['state'].selection).get(req.state, req.state),
                    'reason': req.reason,
                    'rejection_reason': req.rejection_reason if hasattr(req, 'rejection_reason') else '',
                    'create_date': req.create_date.strftime('%Y-%m-%d %H:%M:%S') if req.create_date else '',
                    'approved_date': req.approved_date.strftime('%Y-%m-%d %H:%M:%S') if hasattr(req, 'approved_date') and req.approved_date else '',
                }

                # Add item details
                if req.request_type in ['add_hotel', 'remove_hotel'] and hasattr(req, 'hotel_ids'):
                    data['items'] = req.hotel_ids.mapped('name')
                elif req.request_type in ['add_membership', 'remove_membership'] and hasattr(req, 'membership_purpose_ids'):
                    data['items'] = req.membership_purpose_ids.mapped('name')
                else:
                    data['items'] = []

                requests_data.append(data)

            return {
                'success': True,
                'requests': requests_data
            }

        except Exception as e:
            _logger.error(f"Error getting agency requests: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/profile', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_profile(self, **kwargs):
        """Agency user profile"""
        try:
            user_data = self._get_current_user()
            # Get countries for dropdown
            countries = request.env['res.country'].sudo().search([], order='name')

            # Get cities if user has a country selected
            cities = []
            if user_data.get('country_id'):
                country_id = user_data['country_id'][0] if isinstance(user_data['country_id'], (list, tuple)) else user_data['country_id']
                cities = request.env['res.country.state'].sudo().search([
                    ('country_id', '=', country_id)
                ], order='name')

            values = self._prepare_values(
                page_name='profile',
                countries=countries,
                cities=cities
            )

            # Handle profile update
            if request.httprequest.method == 'POST':
                try:
                    update_data = {
                        'name': kwargs.get('name', '').strip(),
                        'email': kwargs.get('email', '').strip(),
                        'phone': kwargs.get('phone', '').strip(),
                    }

                    # Add country and city if provided
                    if kwargs.get('country_id'):
                        update_data['country_id'] = int(kwargs.get('country_id'))

                    if kwargs.get('city_id'):
                        update_data['city_id'] = int(kwargs.get('city_id'))

                    # Update profile via auth service
                    token = request.session.get('agency_token')
                    auth_service = request.env['agency.auth.service'].sudo()
                    result = auth_service.update_agency_user(user_data['id'], update_data, token)

                    if result['success']:
                        # Clear cache to refresh user data
                        if hasattr(request, '_cached_user_data'):
                            delattr(request, '_cached_user_data')

                        return request.redirect('/agency/settings?success=profile_updated')
                    else:
                        values['error'] = result['message']

                except Exception as e:
                    _logger.error(f"Error updating profile: {str(e)}")
                    values['error'] = _('Failed to update profile. Please try again.')

            return request.render('eth_agency_portal.agency_profile', values)

        except Exception as e:
            _logger.error(f"Error in profile: {str(e)}")
            return request.redirect('/agency/dashboard')

    @http.route('/agency/change-password', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_change_password(self, **kwargs):
        """Change password for logged in users"""
        try:
            values = self._prepare_values(page_name='profile')

            # Handle password change
            if request.httprequest.method == 'POST':
                try:
                    current_password = kwargs.get('current_password', '')
                    new_password = kwargs.get('new_password', '')
                    confirm_password = kwargs.get('confirm_password', '')

                    if not current_password or not new_password or not confirm_password:
                        values['error'] = _('All fields are required.')
                    elif new_password != confirm_password:
                        values['error'] = _('New passwords do not match.')
                    elif len(new_password) < 6:
                        values['error'] = _('New password must be at least 6 characters long.')
                    else:
                        # Change password via auth service
                        token = request.session.get('agency_token')
                        auth_service = request.env['agency.auth.service'].sudo()
                        result = auth_service.change_user_password(token, current_password, new_password)

                        if result['success']:
                            values['success'] = _('Password changed successfully.')
                        else:
                            values['error'] = result['message']

                except Exception as e:
                    _logger.error(f"Error changing password: {str(e)}")
                    values['error'] = _('Failed to change password. Please try again.')

            return request.render('eth_agency_portal.agency_change_password', values)

        except Exception as e:
            _logger.error(f"Error in change password: {str(e)}")
            return request.redirect('/agency/dashboard')

    @http.route('/agency/business-profile', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_business_profile(self, **kwargs):
        """Agency business profile edit page"""
        user_data = self._get_current_user()
        if not user_data:
            return request.redirect('/agency/login')

        agency_id = self._get_agency_id()

        # Get the agency and registration record
        try:
            agency = request.env['travel.agency'].sudo().browse(agency_id)

            # Try to find registration record - use correct model name
            registration = None
            try:
                registration = request.env['agency.registration'].sudo().search([
                    ('agency_id', '=', agency_id)
                ], limit=1)
                _logger.info(f"Found registration: {registration.id if registration else 'None'}")
            except KeyError:
                _logger.warning("agency.registration model not found")

            # Prepare business profile data
            business_profile = {
                'name': agency.name,
                'email': agency.email if hasattr(agency, 'email') else '',
                'phone': agency.phone if hasattr(agency, 'phone') else '',
                'website': agency.website if hasattr(agency, 'website') else '',
                'preferred_language': registration.preferred_language if registration else 'tr',
                'country_id': registration.country_id.id if registration and registration.country_id else None,
                'country_name': registration.country_id.name if registration and registration.country_id else '',
                'city_id': registration.city_id.id if registration and registration.city_id else None,
                'address': registration.address if registration else '',
                'business_registration_number': registration.business_registration_number if registration else '',
                'tax_office': registration.tax_office if registration else '',
                'iata_code': registration.iata_code if registration else '',
                'has_iata_accreditation': registration.has_iata_accreditation if registration else False,
                'confirmation_file_name': registration.confirmation_file_name if registration and registration.confirmation_file_name else None,
                'confirmation_file_url': f'/agency/download-confirmation-file/{registration.id}' if registration and registration.confirmation_file else None,
            }

            _logger.info(f"Business profile data: country_id={business_profile['country_id']}, city_id={business_profile['city_id']}, address={business_profile['address'][:50] if business_profile['address'] else 'None'}")

            # Get countries for dropdown
            countries = request.env['res.country'].sudo().search([], order='name')
            cities = []
            if registration and registration.country_id:
                cities = request.env['res.country.state'].sudo().search([
                    ('country_id', '=', registration.country_id.id)
                ], order='name')
                _logger.info(f"Loaded {len(cities)} cities for country {registration.country_id.name}")

        except Exception as e:
            _logger.error(f"Error getting agency business profile: {str(e)}")
            return request.redirect('/agency/settings')

        values = self._prepare_values(
            page_name='settings',
            business_profile=business_profile,
            countries=countries,
            cities=cities
        )

        # Handle form submission
        if request.httprequest.method == 'POST':
            try:
                # Validate required fields
                if not kwargs.get('preferred_language'):
                    values['error'] = _('Preferred language is mandatory.')
                    return request.render('eth_agency_portal.agency_business_profile_edit', values)

                if not kwargs.get('country_id'):
                    values['error'] = _('Country is required.')
                    return request.render('eth_agency_portal.agency_business_profile_edit', values)

                if not kwargs.get('city_id'):
                    values['error'] = _('City is required.')
                    return request.render('eth_agency_portal.agency_business_profile_edit', values)

                if not kwargs.get('address'):
                    values['error'] = _('Address is required.')
                    return request.render('eth_agency_portal.agency_business_profile_edit', values)

                update_vals = {
                    'preferred_language': kwargs.get('preferred_language'),
                    'country_id': int(kwargs.get('country_id')),
                    'city_id': int(kwargs.get('city_id')),
                    'address': kwargs.get('address', '').strip(),
                    'business_registration_number': kwargs.get('business_registration_number', '').strip(),
                    'tax_office': kwargs.get('tax_office', '').strip(),
                    'iata_code': kwargs.get('iata_code', '').strip(),
                    'has_iata_accreditation': bool(kwargs.get('has_iata_accreditation')),
                }

                # Handle file upload
                if 'confirmation_file' in request.httprequest.files:
                    file = request.httprequest.files['confirmation_file']
                    if file and file.filename:
                        file.seek(0, 2)
                        file_size = file.tell()
                        file.seek(0)

                        if file_size > 5 * 1024 * 1024:
                            values['error'] = _('File size must be less than 5MB.')
                            return request.render('eth_agency_portal.agency_business_profile_edit', values)

                        file_content = file.read()
                        file_encoded = base64.b64encode(file_content)

                        update_vals['confirmation_file'] = file_encoded
                        update_vals['confirmation_file_name'] = file.filename

                # Update registration record
                if registration:
                    agency_update_vals = {
                        'email': kwargs.get('email', '').strip(),
                        'phone': kwargs.get('phone', '').strip(),
                        'website': kwargs.get('website', '').strip(),
                    }
                    agency.write(agency_update_vals)
                    registration.write(update_vals)
                    values['success'] = _('Business information has been updated successfully.')
                else:
                    values['error'] = _('No registration information found.')
                    return request.render('eth_agency_portal.agency_business_profile_edit', values)

                # Refresh business_profile data
                business_profile.update({
                    'email': agency.email if hasattr(agency, 'email') else '',
                    'phone': agency.phone if hasattr(agency, 'phone') else '',
                    'website': agency.website if hasattr(agency, 'website') else '',
                    'preferred_language': registration.preferred_language,
                    'country_id': registration.country_id.id if registration.country_id else None,
                    'country_name': registration.country_id.name if registration.country_id else '',
                    'city_id': registration.city_id.id if hasattr(registration, 'city_id') and registration.city_id else None,
                    'address': registration.address if hasattr(registration, 'address') else '',
                })

                # Refresh cities
                if registration.country_id:
                    cities = request.env['res.country.state'].sudo().search([
                        ('country_id', '=', registration.country_id.id)
                    ], order='name')

                values = self._prepare_values(
                    page_name='settings',
                    business_profile=business_profile,
                    countries=countries,
                    cities=cities,
                    success=_('Business information has been updated successfully.')
                )

            except Exception as e:
                _logger.error(f"Error updating agency business profile: {str(e)}")
                values['error'] = _('An error occurred while updating business information. Please try again.')

        return request.render('eth_agency_portal.agency_business_profile_edit', values)

    @http.route('/agency/download-confirmation-file/<int:registration_id>', type='http', auth="public")
    @require_auth()
    def download_confirmation_file(self, registration_id, **kwargs):
        """Download confirmation file"""
        try:
            agency_id = self._get_agency_id()

            # Get registration
            Registration = request.env.get('travel.agency.registration') or request.env.get('agency.registration')
            if not Registration:
                return request.not_found()

            registration = Registration.sudo().browse(registration_id)

            # Check if user's agency matches the registration
            if not registration.exists() or registration.agency_id.id != agency_id:
                return request.not_found()

            # Check if file exists
            if not registration.confirmation_file or not registration.confirmation_file_name:
                return request.not_found()

            # Decode file
            file_content = base64.b64decode(registration.confirmation_file)

            # Return file as download
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', 'application/octet-stream'),
                    ('Content-Disposition', f'attachment; filename="{registration.confirmation_file_name}"'),
                    ('Content-Length', len(file_content))
                ]
            )

        except Exception as e:
            _logger.error(f"Error downloading confirmation file: {str(e)}")
            return request.not_found()
