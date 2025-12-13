# -*- coding: utf-8 -*-
"""
Hotel Bookings Controller
Mirrors eth_travel_agency_web but uses Travel API instead of ORM
"""
import logging
from datetime import datetime
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase

_logger = logging.getLogger(__name__)


class HotelBookingsController(AgencyPortalBase):
    """Hotel bookings management controllers using Travel API"""

    def _get_token(self):
        """Get auth token from session"""
        return request.session.get('agency_token')

    def _convert_date_to_api_format(self, date_str):
        """Convert date from YYYY-MM-DD to DD.MM.YYYY format"""
        if not date_str:
            return None
        try:
            if '-' in date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                return date_obj.strftime('%d.%m.%Y')
            return date_str
        except ValueError:
            return date_str

    @http.route('/agency/hotel-bookings', type='http', auth="public", website=True, csrf=False)
    def hotel_bookings(self, **kw):
        """Main hotel bookings page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            user_data = self._get_current_user()
            agency_data = self._get_agency_data()

            # Check if agency has Sales purpose
            if not agency_data or not agency_data.get('has_sales', False):
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='hotel-bookings',
                        message=_('Your agency does not have Sales membership. Please contact administrator.')
                    ))

            # Check permissions
            permissions = user_data.get('permissions', {}) if user_data else {}
            can_manage = permissions.get('can_manage_bookings', True) if permissions else True

            if not can_manage:
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='hotel-bookings',
                        message=_('You do not have permission to manage hotel bookings.')
                    ))

            # Get wallet balance
            wallet_balance = 0
            try:
                token = self._get_token()
                api_client = request.env['travel.api.client'].sudo()
                result = api_client.get_booking_wallet_balance(token)
                if result.get('success'):
                    wallet_balance = result.get('data', {}).get('balance', 0)
            except Exception as e:
                _logger.warning(f"Could not get wallet balance: {e}")

            values = self._prepare_values(
                page_name='hotel-bookings',
                wallet_balance=wallet_balance
            )
            return request.render('eth_agency_portal.agency_hotel_bookings', values)

        except Exception as e:
            _logger.error(f"Error in hotel bookings: {str(e)}", exc_info=True)
            return request.redirect('/agency/dashboard')

    # ==================== API Endpoints ====================

    @http.route('/agency/api/hotel-bookings/hotels', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hotels_for_search(self, **kw):
        """Get hotels list for search dropdown"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            # Get hotels (either interested hotels or all hotels)
            result = api_client.get_agency_interested_hotels(token)

            if result.get('success'):
                hotels = result.get('data', [])
                # If no interested hotels, get all hotels
                if not hotels:
                    all_hotels_result = api_client.get_hotels({'status': 'active'})
                    if all_hotels_result.get('success'):
                        hotels = all_hotels_result.get('data', {}).get('hotels', [])

                return {'success': True, 'data': hotels}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get hotels')}

        except Exception as e:
            _logger.error(f"Error getting hotels: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/markets', type='json', auth='public', methods=['POST'], csrf=False)
    def get_markets_for_search(self, **kw):
        """Get markets list for search dropdown"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            result = api_client.get_agency_markets(token)

            if result.get('success'):
                data = result.get('data', {})
                return {
                    'success': True,
                    'data': data.get('markets', []),
                    'default_market_id': data.get('default_market_id')
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get markets')}

        except Exception as e:
            _logger.error(f"Error getting markets: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/search', type='json', auth='public', methods=['POST'], csrf=False)
    def search_hotel_rooms(self, hotel_id=None, market_id=None, checkin=None, checkout=None,
                          adults=2, children=0, child_ages=None, **kw):
        """Search hotel rooms and rates via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not all([hotel_id, market_id, checkin, checkout]):
                return {'success': False, 'error': 'Missing required parameters'}

            # Convert dates to API format if needed
            checkin_formatted = self._convert_date_to_api_format(checkin) if '-' in checkin else checkin
            checkout_formatted = self._convert_date_to_api_format(checkout) if '-' in checkout else checkout

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            search_data = {
                'hotel_id': int(hotel_id),
                'market_id': int(market_id),
                'checkin': checkin_formatted,
                'checkout': checkout_formatted,
                'adults': int(adults),
                'children': int(children) if children else 0,
                'child_ages': child_ages or []
            }

            result = api_client.search_hotel_rooms(token, search_data)

            if result.get('success'):
                return {'success': True, 'data': result.get('data', {})}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to search rooms')}

        except Exception as e:
            _logger.error(f"Error searching hotel rooms: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/wallet-balance', type='json', auth='public', methods=['POST'], csrf=False)
    def get_wallet_balance(self, **kw):
        """Get agency wallet balance for bonus usage"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            result = api_client.get_booking_wallet_balance(token)

            if result.get('success'):
                return {'success': True, 'data': result.get('data', {})}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get wallet balance')}

        except Exception as e:
            _logger.error(f"Error getting wallet balance: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_hotel_booking(self, hotel_id=None, room_id=None, rate_id=None, market_id=None,
                            checkin=None, checkout=None, adults=2, children=0,
                            child_ages=None, guest_name=None, guest_surname=None,
                            guest_email=None, guest_phone=None, special_requests=None,
                            room_total=0, discount=0, bonus_used=0, final_total=0,
                            currency='EUR', **kw):
        """Create a new hotel booking via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not all([hotel_id, room_id, market_id, checkin, checkout, guest_name, guest_surname]):
                return {'success': False, 'error': 'Missing required parameters'}

            # Convert dates to API format
            checkin_formatted = self._convert_date_to_api_format(checkin) if '-' in checkin else checkin
            checkout_formatted = self._convert_date_to_api_format(checkout) if '-' in checkout else checkout

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            booking_data = {
                'hotel_id': int(hotel_id),
                'room_id': int(room_id),
                'market_id': int(market_id),
                'checkin': checkin_formatted,
                'checkout': checkout_formatted,
                'adults': int(adults),
                'children': int(children) if children else 0,
                'child_ages': child_ages or [],
                'guest_name': guest_name,
                'guest_surname': guest_surname,
                'guest_email': guest_email or '',
                'guest_phone': guest_phone or '',
                'special_requests': special_requests or '',
                'room_total': float(room_total),
                'discount': float(discount),
                'bonus_used': float(bonus_used),
                'final_total': float(final_total),
                'currency': currency
            }

            if rate_id:
                booking_data['rate_id'] = int(rate_id)

            result = api_client.create_hotel_booking(token, booking_data)

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {}),
                    'message': 'Booking created successfully'
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to create booking')}

        except Exception as e:
            _logger.error(f"Error creating hotel booking: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/list', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hotel_bookings_list(self, **kw):
        """Get hotel bookings list via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            result = api_client.get_hotel_bookings(token)

            if result.get('success'):
                data = result.get('data', {})
                return {
                    'success': True,
                    'data': {
                        'bookings': data.get('bookings', []),
                        'stats': data.get('stats', {})
                    }
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get bookings')}

        except Exception as e:
            _logger.error(f"Error getting hotel bookings list: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/detail', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hotel_booking_detail(self, booking_id=None, **kw):
        """Get hotel booking details via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not booking_id:
                return {'success': False, 'error': 'Booking ID required'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            result = api_client.get_hotel_booking(token, int(booking_id))

            if result.get('success'):
                return {'success': True, 'data': result.get('data', {})}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get booking details')}

        except Exception as e:
            _logger.error(f"Error getting booking detail: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/update', type='json', auth='public', methods=['POST'], csrf=False)
    def update_hotel_booking(self, booking_id=None, guest_name=None, guest_surname=None,
                            guest_email=None, guest_phone=None, special_requests=None, **kw):
        """Update hotel booking via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not booking_id:
                return {'success': False, 'error': 'Booking ID required'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            update_data = {}
            if guest_name is not None:
                update_data['guest_name'] = guest_name
            if guest_surname is not None:
                update_data['guest_surname'] = guest_surname
            if guest_email is not None:
                update_data['guest_email'] = guest_email
            if guest_phone is not None:
                update_data['guest_phone'] = guest_phone
            if special_requests is not None:
                update_data['special_requests'] = special_requests

            result = api_client.update_hotel_booking(token, int(booking_id), update_data)

            if result.get('success'):
                return {'success': True, 'message': 'Booking updated successfully'}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to update booking')}

        except Exception as e:
            _logger.error(f"Error updating booking: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-bookings/delete', type='json', auth='public', methods=['POST'], csrf=False)
    def delete_hotel_booking(self, booking_id=None, **kw):
        """Delete/Cancel hotel booking via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not booking_id:
                return {'success': False, 'error': 'Booking ID required'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            result = api_client.delete_hotel_booking(token, int(booking_id))

            if result.get('success'):
                data = result.get('data', {})
                return {
                    'success': True,
                    'message': 'Booking deleted successfully',
                    'bonus_refunded': data.get('bonus_refunded', 0)
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to delete booking')}

        except Exception as e:
            _logger.error(f"Error deleting booking: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
