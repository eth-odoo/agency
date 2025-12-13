# -*- coding: utf-8 -*-
"""
Bonus Reservation Management Controller
Mirrors eth_travel_agency_web but uses Travel API instead of ORM
"""
import logging
import base64
from datetime import datetime
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase

_logger = logging.getLogger(__name__)


class BonusReservationController(AgencyPortalBase):
    """Bonus reservation management controllers using Travel API"""

    def _convert_date_format(self, date_str):
        """Convert date from DD.MM.YYYY to YYYY-MM-DD format"""
        if not date_str:
            return None
        try:
            if '.' in date_str:
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                return date_obj.strftime('%Y-%m-%d')
            elif '-' in date_str:
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
            return date_str
        except ValueError as e:
            _logger.warning(f"Date format conversion failed for {date_str}: {str(e)}")
            return date_str

    def _get_token(self):
        """Get auth token from session"""
        return request.session.get('agency_token')

    @http.route('/agency/bonus-reservation', type='http', auth="public", website=True, csrf=False)
    def bonus_reservation(self, **kw):
        """Main bonus reservation page"""
        try:
            # Check authentication
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            user_data = self._get_current_user()
            agency_data = self._get_agency_data()

            # Check if agency has Bonus purpose
            if not agency_data or not agency_data.get('has_bonus', False):
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='bonus-reservation',
                        message=_('Your agency does not have Bonus membership. Please contact administrator.')
                    ))

            # Check permissions - allow if can_manage_bookings or if permissions not set
            permissions = user_data.get('permissions', {}) if user_data else {}
            can_manage = permissions.get('can_manage_bookings', True) if permissions else True

            if not can_manage:
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='bonus-reservation',
                        message=_('You do not have permission to manage bonus reservations.')
                    ))

            values = self._prepare_values(page_name='bonus-reservation')
            return request.render('eth_agency_portal.agency_bonus_reservation', values)

        except Exception as e:
            _logger.error(f"Error in bonus reservation: {str(e)}", exc_info=True)
            return request.redirect('/agency/dashboard')

    # ==================== API Endpoints ====================

    @http.route('/agency/api/bonus-reservations', type='json', auth='public', methods=['POST'], csrf=False)
    def get_bonus_reservations(self, filters=None, **kw):
        """Get list of bonus reservations via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            # Get reservations from Travel API
            result = api_client.get_bonus_reservations(token, filters or {})

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {'reservations': []})
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get reservations')}

        except Exception as e:
            _logger.error(f"Error in get_bonus_reservations: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/bonus-reservations/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_bonus_reservation(self, reservation_data=None, **kw):
        """Create new bonus reservation via Travel API"""
        try:
            _logger.info(f"Creating bonus reservation with data: {reservation_data}")

            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not reservation_data:
                return {'success': False, 'error': 'No reservation data provided'}

            # Validate required fields
            if not reservation_data.get('market_id'):
                return {'success': False, 'error': 'Market is required. Please select a market.'}

            # Convert date fields
            if reservation_data.get('booking_date'):
                reservation_data['booking_date'] = self._convert_date_format(reservation_data['booking_date'])
            if reservation_data.get('checkin_date'):
                reservation_data['checkin_date'] = self._convert_date_format(reservation_data['checkin_date'])
            if reservation_data.get('checkout_date'):
                reservation_data['checkout_date'] = self._convert_date_format(reservation_data['checkout_date'])

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            # Create via Travel API
            result = api_client.create_bonus_reservation(token, reservation_data)

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to create reservation')}

        except Exception as e:
            _logger.error(f"Error in create_bonus_reservation: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/bonus-reservations/update', type='json', auth='public', methods=['POST'], csrf=False)
    def update_bonus_reservation(self, reservation_data=None, **kw):
        """Update existing bonus reservation via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not reservation_data or not reservation_data.get('id'):
                return {'success': False, 'error': 'Reservation ID required'}

            # Convert date fields
            if reservation_data.get('booking_date'):
                reservation_data['booking_date'] = self._convert_date_format(reservation_data['booking_date'])
            if reservation_data.get('checkin_date'):
                reservation_data['checkin_date'] = self._convert_date_format(reservation_data['checkin_date'])
            if reservation_data.get('checkout_date'):
                reservation_data['checkout_date'] = self._convert_date_format(reservation_data['checkout_date'])

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            # Update via Travel API
            result = api_client.update_bonus_reservation(token, reservation_data)

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to update reservation')}

        except Exception as e:
            _logger.error(f"Error in update_bonus_reservation: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/bonus-reservations/delete', type='json', auth='public', methods=['POST'], csrf=False)
    def delete_bonus_reservation(self, reservation_id=None, **kw):
        """Delete bonus reservation via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not reservation_id:
                return {'success': False, 'error': 'Reservation ID required'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            # Delete via Travel API
            result = api_client.delete_bonus_reservation(token, reservation_id)

            if result.get('success'):
                return {'success': True}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to delete reservation')}

        except Exception as e:
            _logger.error(f"Error in delete_bonus_reservation: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/bonus-reservations/download-file/<int:reservation_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def download_confirmation_file(self, reservation_id, **kw):
        """Download confirmation file for a reservation via Travel API"""
        try:
            if not self._is_authenticated():
                return request.not_found()

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            # Get file from Travel API
            result = api_client.get_reservation_file(token, reservation_id)

            if not result.get('success') or not result.get('data'):
                return request.not_found()

            file_data = result['data']
            file_content = base64.b64decode(file_data.get('content', ''))
            filename = file_data.get('filename', f'confirmation_{reservation_id}.pdf')

            # Determine content type
            content_type = 'application/octet-stream'
            if filename.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif filename.lower().endswith('.png'):
                content_type = 'image/png'

            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', content_type),
                    ('Content-Disposition', f'inline; filename="{filename}"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error downloading confirmation file: {str(e)}")
            return request.not_found()

    @http.route('/agency/api/markets', type='json', auth='public', methods=['POST'], csrf=False)
    def get_markets(self, **kw):
        """Get markets based on agency and user's country via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            # Use get_agency_markets which returns markets based on user/agency country
            result = api_client.get_agency_markets(token)

            if result.get('success'):
                data = result.get('data', {})
                return {
                    'success': True,
                    'data': {
                        'markets': data.get('markets', []),
                        'default_market_id': data.get('default_market_id'),
                        'is_single_market': data.get('is_single_market', False)
                    }
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get markets')}

        except Exception as e:
            _logger.error(f"Error in get_markets: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/agency-hotels', type='json', auth='public', methods=['POST'], csrf=False)
    def get_agency_hotels(self, **kw):
        """Get hotels associated with the agency via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            result = api_client.get_agency_interested_hotels(token)

            if result.get('success'):
                return {
                    'success': True,
                    'data': {'hotels': result.get('data', [])}
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get hotels')}

        except Exception as e:
            _logger.error(f"Error in get_agency_hotels: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/hotel-rooms', type='json', auth='public', methods=['POST'], csrf=False)
    def get_hotel_rooms(self, hotel_id=None, **kw):
        """Get rooms for a specific hotel via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not hotel_id:
                return {'success': False, 'error': 'Hotel ID required'}

            api_client = request.env['travel.api.client'].sudo()

            # Use get_hotel_room_types (doesn't need token)
            result = api_client.get_hotel_room_types(hotel_id)

            if result.get('success'):
                return {
                    'success': True,
                    'data': {'rooms': result.get('data', [])}
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get rooms')}

        except Exception as e:
            _logger.error(f"Error in get_hotel_rooms: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/operators', type='json', auth='public', methods=['POST'], csrf=False)
    def get_operators(self, **kw):
        """Get all operators via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            api_client = request.env['travel.api.client'].sudo()

            # get_operators() doesn't need token
            result = api_client.get_operators()

            if result.get('success'):
                return {
                    'success': True,
                    'data': {'operators': result.get('data', [])}
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get operators')}

        except Exception as e:
            _logger.error(f"Error in get_operators: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/calculate-bonus', type='json', auth='public', methods=['POST'], csrf=False)
    def calculate_bonus(self, hotel_id=None, room_id=None, checkin_date=None,
                        checkout_date=None, total_amount=None, **kw):
        """Calculate bonus commission via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            api_client = request.env['travel.api.client'].sudo()

            data = {
                'hotel_id': hotel_id,
                'room_id': room_id,
                'checkin_date': checkin_date,
                'checkout_date': checkout_date,
                'total_amount': total_amount
            }

            result = api_client.calculate_bonus(token, data)

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to calculate bonus')}

        except Exception as e:
            _logger.error(f"Error in calculate_bonus: {str(e)}")
            return {'success': False, 'error': str(e)}

    # Backward compatibility endpoints
    @http.route('/agency/api/hotels', type='json', auth='public', methods=['POST'], csrf=False)
    def get_all_hotels(self, **kw):
        """Get all hotels (backward compatibility)"""
        return self.get_agency_hotels(**kw)

    @http.route('/agency/api/room-types', type='json', auth='public', methods=['POST'], csrf=False)
    def get_room_types(self, **kw):
        """Get all room types (backward compatibility)"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            return {
                'success': True,
                'data': {'room_types': []}
            }

        except Exception as e:
            _logger.error(f"Error in get_room_types: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/currencies', type='json', auth='public', methods=['POST'], csrf=False)
    def get_currencies(self, **kw):
        """Get currencies"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            return {
                'success': True,
                'data': {
                    'currencies': [
                        {'id': 1, 'name': 'USD', 'symbol': '$'},
                        {'id': 2, 'name': 'EUR', 'symbol': '\u20ac'},
                        {'id': 3, 'name': 'TRY', 'symbol': '\u20ba'},
                    ]
                }
            }

        except Exception as e:
            _logger.error(f"Error in get_currencies: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== Voucher OCR ====================

    @http.route('/agency/api/scan-voucher', type='json', auth='public', methods=['POST'], csrf=False)
    def scan_voucher(self, file_data=None, filename=None, **kw):
        """Scan voucher file and extract data using OCR"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not file_data:
                return {'success': False, 'error': 'No file data provided'}

            # Import OCR utilities
            from ..utils.voucher_ocr import extract_voucher_data

            # Decode base64 file
            import base64
            file_content = base64.b64decode(file_data)

            # Extract data from voucher (pass env for System Parameters access)
            result = extract_voucher_data(file_content, filename or 'voucher.pdf', env=request.env)

            if result.get('success'):
                return {
                    'success': True,
                    'data': result.get('data', {})
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to extract voucher data')}

        except ImportError:
            _logger.warning("Voucher OCR module not available")
            return {'success': False, 'error': 'OCR feature not available. Please enter data manually.'}
        except Exception as e:
            _logger.error(f"Error in scan_voucher: {str(e)}")
            return {'success': False, 'error': str(e)}
