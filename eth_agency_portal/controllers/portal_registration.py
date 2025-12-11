# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import logging

_logger = logging.getLogger(__name__)


class AgencyRegistrationPortal(http.Controller):

    def _get_hotels(self):
        """Get hotels if hotel module is installed"""
        try:
            Hotel = request.env['eth.travel.hotel']
            return Hotel.sudo().search([('status', '=', 'active')], order='name')
        except Exception:
            # Hotel module not installed
            return False

    @http.route(['/agency/register'], type='http', auth="public", website=True)
    def agency_registration_form(self, **kw):
        """Registration form for travel agencies"""
        countries = request.env['res.country'].sudo().search([])

        # Get membership purposes
        membership_purposes = request.env['agency.membership.purpose'].sudo().search([
            ('active', '=', True)
        ], order='sequence')

        # Try to get hotels (optional - only if hotel module installed)
        hotels = self._get_hotels()

        values = {
            'countries': countries,
            'membership_purposes': membership_purposes,
            'hotels': hotels,
            'page_name': 'agency_registration',
            'post': {},
            'errors': {},
        }
        return request.render('eth_agency_portal.agency_registration_form', values)

    @http.route(['/agency/get_cities/<int:country_id>'], type='http', auth="public", website=True)
    def get_cities(self, country_id, **kw):
        """Get cities for a specific country"""
        try:
            cities = request.env['res.country.state'].sudo().search([
                ('country_id', '=', country_id)
            ], order='name')

            result = {
                'success': True,
                'cities': [{
                    'id': city.id,
                    'name': city.name,
                    'code': city.code
                } for city in cities]
            }
            return request.make_json_response(result)
        except Exception as e:
            _logger.error(f'Error loading cities for country {country_id}: {e}')
            return request.make_json_response({
                'success': False,
                'cities': [],
                'error': str(e)
            })

    @http.route(['/agency/register/submit'], type='http', auth="public",
                website=True, methods=['POST'], csrf=True)
    def submit_agency_registration(self, **post):
        """Submit agency registration"""
        try:
            # Validate required fields
            required_fields = [
                'agency_name', 'authorized_first_name', 'authorized_last_name',
                'authorized_email', 'country_id', 'address', 'preferred_language'
            ]

            errors = {}
            for field in required_fields:
                if not post.get(field):
                    errors[field] = 'This field is required.'

            # Validate email
            if post.get('authorized_email') and '@' not in post.get('authorized_email'):
                errors['authorized_email'] = 'Please enter a valid email address.'

            # Validate terms acceptance
            if not post.get('terms_accepted'):
                errors['terms_accepted'] = 'You must accept the terms and conditions.'

            # Validate membership purposes
            membership_purpose_ids = request.httprequest.form.getlist('membership_purpose_ids')
            if not membership_purpose_ids:
                errors['membership_purpose_ids'] = 'Please select at least one membership purpose.'

            if errors:
                countries = request.env['res.country'].sudo().search([])
                membership_purposes = request.env['agency.membership.purpose'].sudo().search([
                    ('active', '=', True)
                ], order='sequence')
                hotels = self._get_hotels()

                values = {
                    'countries': countries,
                    'membership_purposes': membership_purposes,
                    'hotels': hotels,
                    'post': post,
                    'errors': errors,
                    'page_name': 'agency_registration',
                }
                return request.render('eth_agency_portal.agency_registration_form', values)

            # Handle file upload
            confirmation_file = None
            confirmation_file_name = None
            if post.get('confirmation_file'):
                confirmation_file = base64.b64encode(post.get('confirmation_file').read())
                confirmation_file_name = post.get('confirmation_file').filename

            # Process membership purposes
            membership_purpose_ids_processed = []
            if membership_purpose_ids:
                membership_purpose_ids_processed = [(6, 0, [int(pid) for pid in membership_purpose_ids])]

            # Process interested hotels (if available)
            interested_hotel_ids = request.httprequest.form.getlist('interested_hotel_ids')
            interested_hotel_ids_processed = []
            if interested_hotel_ids:
                interested_hotel_ids_processed = [(6, 0, [int(hid) for hid in interested_hotel_ids])]

            # Create registration
            registration_data = {
                'agency_name': post.get('agency_name'),
                'authorized_first_name': post.get('authorized_first_name'),
                'authorized_last_name': post.get('authorized_last_name'),
                'authorized_email': post.get('authorized_email'),
                'phone_number': post.get('phone_number'),
                'country_id': int(post.get('country_id')),
                'city_id': int(post.get('city_id')) if post.get('city_id') else False,
                'address': post.get('address'),
                'preferred_language': post.get('preferred_language'),
                'membership_purpose_ids': membership_purpose_ids_processed,
                'business_registration_number': post.get('business_registration_number'),
                'tax_office': post.get('tax_office'),
                'iata_code': post.get('iata_code'),
                'has_iata_accreditation': bool(post.get('has_iata_accreditation')),
                'confirmation_file': confirmation_file,
                'confirmation_file_name': confirmation_file_name,
                'notes': post.get('notes'),
            }

            # Add interested hotels if the field exists on the model
            if interested_hotel_ids_processed:
                try:
                    # Check if field exists
                    if 'interested_hotel_ids' in request.env['agency.registration']._fields:
                        registration_data['interested_hotel_ids'] = interested_hotel_ids_processed
                except Exception:
                    pass

            registration = request.env['agency.registration'].sudo().create(registration_data)
            registration.action_submit()

            _logger.info(f'New agency registration created: {registration.id}')
            return request.redirect(f'/agency/register/success?registration_id={registration.id}')

        except Exception as e:
            _logger.error(f'Error creating agency registration: {e}')
            countries = request.env['res.country'].sudo().search([])
            membership_purposes = request.env['agency.membership.purpose'].sudo().search([
                ('active', '=', True)
            ], order='sequence')
            hotels = self._get_hotels()

            values = {
                'countries': countries,
                'membership_purposes': membership_purposes,
                'hotels': hotels,
                'post': post,
                'errors': {},
                'error_message': f'An error occurred: {str(e)}',
                'page_name': 'agency_registration',
            }
            return request.render('eth_agency_portal.agency_registration_form', values)

    @http.route(['/agency/register/success'], type='http', auth="public", website=True)
    def agency_registration_success(self, registration_id=None, **kw):
        """Registration success page"""
        registration = None
        if registration_id:
            registration = request.env['agency.registration'].sudo().browse(int(registration_id))

        values = {
            'registration': registration,
            'page_name': 'agency_registration_success',
        }
        return request.render('eth_agency_portal.agency_registration_success', values)

    @http.route(['/agency/terms'], type='http', auth="public", website=True)
    def agency_terms_conditions(self, **kw):
        """Terms and conditions page"""
        return request.render('eth_agency_portal.agency_terms_conditions', {
            'page_name': 'agency_terms',
        })
