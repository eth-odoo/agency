# -*- coding: utf-8 -*-
"""
Travel API Client - Communicates with Travel system via HTTP API
"""
import logging
import json
import requests
from odoo import models, api

_logger = logging.getLogger(__name__)


class TravelAPIClient(models.AbstractModel):
    _name = 'travel.api.client'
    _description = 'Travel API Client'

    def _get_api_config(self):
        """Get API configuration"""
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'base_url': ICP.get_param('eth_agency_portal.travel_api_url', ''),
            'api_key': ICP.get_param('eth_agency_portal.travel_api_key', ''),
            'timeout': int(ICP.get_param('eth_agency_portal.api_timeout', '30')),
        }

    def _make_request(self, method, endpoint, data=None, agency_token=None):
        """Make HTTP request to Travel API"""
        config = self._get_api_config()

        if not config['base_url']:
            _logger.error("Travel API URL not configured")
            return {'success': False, 'error': 'API not configured'}

        url = f"{config['base_url'].rstrip('/')}{endpoint}"

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': config['api_key'],
        }

        if agency_token:
            headers['X-Agency-Token'] = agency_token

        try:
            if method.upper() == 'GET':
                response = requests.get(
                    url,
                    headers=headers,
                    params=data,
                    timeout=config['timeout']
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=config['timeout']
                )
            elif method.upper() == 'PUT':
                response = requests.put(
                    url,
                    headers=headers,
                    json=data,
                    timeout=config['timeout']
                )
            elif method.upper() == 'DELETE':
                response = requests.delete(
                    url,
                    headers=headers,
                    timeout=config['timeout']
                )
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}

            result = response.json()
            return result

        except requests.exceptions.Timeout:
            _logger.error(f"Travel API timeout: {endpoint}")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.ConnectionError:
            _logger.error(f"Travel API connection error: {endpoint}")
            return {'success': False, 'error': 'Connection error'}
        except json.JSONDecodeError:
            _logger.error(f"Invalid JSON response from Travel API: {endpoint}")
            return {'success': False, 'error': 'Invalid response'}
        except Exception as e:
            _logger.error(f"Travel API error: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== Bonus API Methods ====================

    def get_bonus_wallet(self, agency_token):
        """Get agency bonus wallet"""
        return self._make_request('GET', '/api/travel/bonus/wallet', agency_token=agency_token)

    def get_bonus_reservations(self, agency_token, params=None):
        """Get agency bonus reservations"""
        return self._make_request('GET', '/api/travel/bonus/reservations', data=params, agency_token=agency_token)

    def get_bonus_reservation(self, agency_token, reservation_id):
        """Get single bonus reservation"""
        return self._make_request('GET', f'/api/travel/bonus/reservations/{reservation_id}', agency_token=agency_token)

    def create_bonus_reservation(self, agency_token, data):
        """Create bonus reservation"""
        return self._make_request('POST', '/api/travel/bonus/reservations', data=data, agency_token=agency_token)

    def update_bonus_reservation(self, agency_token, data):
        """Update bonus reservation"""
        reservation_id = data.get('id')
        return self._make_request('PUT', f'/api/travel/bonus/reservations/{reservation_id}', data=data, agency_token=agency_token)

    def delete_bonus_reservation(self, agency_token, reservation_id):
        """Delete bonus reservation"""
        return self._make_request('DELETE', f'/api/travel/bonus/reservations/{reservation_id}', agency_token=agency_token)

    def get_reservation_file(self, agency_token, reservation_id):
        """Get reservation confirmation file"""
        return self._make_request('GET', f'/api/travel/bonus/reservations/{reservation_id}/file', agency_token=agency_token)

    def get_bonus_contracts(self, agency_token, params=None):
        """Get bonus contracts"""
        return self._make_request('GET', '/api/travel/bonus/contracts', data=params, agency_token=agency_token)

    def calculate_bonus(self, agency_token, data):
        """Calculate bonus for a reservation"""
        return self._make_request('POST', '/api/travel/bonus/calculate', data=data, agency_token=agency_token)

    # ==================== Hotel API Methods ====================

    def get_hotels(self, params=None):
        """Get list of hotels"""
        return self._make_request('GET', '/api/travel/hotels', data=params)

    def get_hotel(self, hotel_id):
        """Get hotel details"""
        return self._make_request('GET', f'/api/travel/hotels/{hotel_id}')

    def get_hotel_room_types(self, hotel_id):
        """Get room types for a hotel"""
        return self._make_request('GET', f'/api/travel/hotels/{hotel_id}/room-types')

    def get_hotel_rooms(self, hotel_id):
        """Alias for get_hotel_room_types"""
        return self.get_hotel_room_types(hotel_id)

    def get_markets(self):
        """Get available markets"""
        return self._make_request('GET', '/api/travel/markets')

    def get_agency_markets(self, agency_token):
        """Get markets based on agency and user's country"""
        return self._make_request('GET', '/api/travel/agency/markets', agency_token=agency_token)

    def get_operators(self):
        """Get available operators"""
        return self._make_request('GET', '/api/travel/operators')

    def get_countries(self):
        """Get countries with hotels"""
        return self._make_request('GET', '/api/travel/countries')

    def get_agency_interested_hotels(self, agency_token):
        """Get agency's interested hotels"""
        return self._make_request('GET', '/api/travel/agency/interested-hotels', agency_token=agency_token)

    def update_agency_interested_hotels(self, agency_token, data):
        """Update agency's interested hotels"""
        return self._make_request('POST', '/api/travel/agency/interested-hotels', data=data, agency_token=agency_token)

    # ==================== Agency API Methods ====================

    def agency_login(self, email, password):
        """Authenticate agency user via Travel API"""
        return self._make_request('POST', '/api/travel/agency/login', data={
            'email': email,
            'password': password
        })

    def agency_logout(self, agency_token):
        """Logout agency user"""
        return self._make_request('POST', '/api/travel/agency/logout', agency_token=agency_token)

    def validate_token(self, token):
        """Validate agency token"""
        return self._make_request('POST', '/api/travel/agency/validate-token', data={'token': token})

    def get_agency_profile(self, agency_token):
        """Get agency profile"""
        return self._make_request('GET', '/api/travel/agency/profile', agency_token=agency_token)

    def get_agency_users(self, agency_token):
        """Get agency users"""
        return self._make_request('GET', '/api/travel/agency/users', agency_token=agency_token)

    def get_membership_purposes(self):
        """Get membership purposes"""
        return self._make_request('GET', '/api/travel/agency/membership-purposes')

    # ==================== Hotel Booking API Methods ====================

    def search_hotel_rooms(self, agency_token, data):
        """Search hotel rooms and rates"""
        return self._make_request('POST', '/api/travel/bookings/search', data=data, agency_token=agency_token)

    def get_hotel_bookings(self, agency_token, params=None):
        """Get hotel bookings for agency"""
        return self._make_request('GET', '/api/travel/bookings', data=params, agency_token=agency_token)

    def get_hotel_booking(self, agency_token, booking_id):
        """Get single hotel booking"""
        return self._make_request('GET', f'/api/travel/bookings/{booking_id}', agency_token=agency_token)

    def create_hotel_booking(self, agency_token, data):
        """Create hotel booking"""
        return self._make_request('POST', '/api/travel/bookings', data=data, agency_token=agency_token)

    def update_hotel_booking(self, agency_token, booking_id, data):
        """Update hotel booking"""
        return self._make_request('PUT', f'/api/travel/bookings/{booking_id}', data=data, agency_token=agency_token)

    def delete_hotel_booking(self, agency_token, booking_id):
        """Delete hotel booking"""
        return self._make_request('DELETE', f'/api/travel/bookings/{booking_id}', agency_token=agency_token)

    def get_booking_wallet_balance(self, agency_token):
        """Get wallet balance for booking"""
        return self._make_request('GET', '/api/travel/bookings/wallet-balance', agency_token=agency_token)

    # ==================== Ticket API Methods ====================

    def _get_ticket_api_config(self):
        """Get Ticket API configuration"""
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'base_url': ICP.get_param('eth_ticket.api_url', ''),
            'api_key': ICP.get_param('eth_ticket.api_key', ''),
        }

    def _make_ticket_request(self, method, endpoint, data=None):
        """Make HTTP request to Ticket API"""
        config = self._get_ticket_api_config()

        if not config['base_url']:
            _logger.error("Ticket API URL not configured")
            return {'success': False, 'error': 'Ticket API not configured'}

        url = f"{config['base_url'].rstrip('/')}{endpoint}"

        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': config['api_key'],
        }

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=30)
                return response.json()
            elif method.upper() == 'POST':
                # JSON-RPC format for POST
                payload = {
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'params': data or {},
                    'id': int(self.env.cr.now().timestamp() * 1000) if hasattr(self.env.cr, 'now') else 1
                }
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                result = response.json()
                if 'result' in result:
                    return result['result']
                elif 'error' in result:
                    return {'success': False, 'error': result['error'].get('message', 'Unknown error')}
                return result
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}

        except requests.exceptions.Timeout:
            _logger.error(f"Ticket API timeout: {endpoint}")
            return {'success': False, 'error': 'Request timeout'}
        except requests.exceptions.ConnectionError:
            _logger.error(f"Ticket API connection error: {endpoint}")
            return {'success': False, 'error': 'Connection error'}
        except json.JSONDecodeError:
            _logger.error(f"Invalid JSON response from Ticket API: {endpoint}")
            return {'success': False, 'error': 'Invalid response'}
        except Exception as e:
            _logger.error(f"Ticket API error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_ticket_products(self, ticket_type=None, currency='EUR', visit_date=None):
        """Get ticket products"""
        params = {'currency': currency}
        if ticket_type:
            params['ticket_type'] = ticket_type
        if visit_date:
            params['visit_date'] = visit_date
        return self._make_ticket_request('GET', '/api/ticket/products', params)

    def get_ticket_product(self, product_id, visit_date=None):
        """Get single ticket product"""
        params = {}
        if visit_date:
            params['visit_date'] = visit_date
        return self._make_ticket_request('GET', f'/api/ticket/product/{product_id}', params)

    def get_ticket_stock(self, product_id, visit_date):
        """Get ticket stock for a product on specific date"""
        return self._make_ticket_request('GET', '/api/ticket/stock', {
            'product_id': product_id,
            'visit_date': visit_date
        })

    def get_ticket_stock_bulk(self, product_ids, visit_date):
        """Get stock for multiple products"""
        return self._make_ticket_request('POST', '/api/ticket/stock/bulk', {
            'product_ids': product_ids,
            'visit_date': visit_date
        })

    def get_ticket_types(self):
        """Get available ticket types"""
        return self._make_ticket_request('GET', '/api/ticket/types')

    def create_ticket_order(self, partner_id, visit_date, lines, agency_ref=None):
        """Create ticket order"""
        data = {
            'partner_id': partner_id,
            'visit_date': visit_date,
            'lines': lines
        }
        if agency_ref:
            data['agency_ref'] = agency_ref
        return self._make_ticket_request('POST', '/api/ticket/order/create', data)

    def get_ticket_order(self, order_id):
        """Get ticket order details"""
        return self._make_ticket_request('GET', f'/api/ticket/order/{order_id}')

    def confirm_ticket_order(self, order_id):
        """Confirm ticket order"""
        return self._make_ticket_request('POST', f'/api/ticket/order/{order_id}/confirm')

    def cancel_ticket_order(self, order_id):
        """Cancel ticket order"""
        return self._make_ticket_request('POST', f'/api/ticket/order/{order_id}/cancel')
