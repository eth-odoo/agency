# -*- coding: utf-8 -*-
"""
Bonus Portal Controller - Reservations, Wallet, Contracts
"""
import logging
from odoo import http, _
from odoo.http import request
from .portal_main import PortalMain

_logger = logging.getLogger(__name__)


class PortalBonus(PortalMain):
    """Portal controller for bonus features"""

    # ==================== Wallet ====================

    @http.route('/agency/bonus/wallet', type='http', auth='public', website=True)
    def portal_wallet(self, **kwargs):
        """Bonus wallet page"""
        if not self._check_login():
            return request.redirect('/agency/login')

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        # Get wallet data from Travel API
        wallet_data = {'balance': 0, 'currency': 'EUR', 'entries': []}
        result = api_client.get_bonus_wallet(token)
        if result.get('success') and result.get('data'):
            wallet_data = result['data']

        context = self._portal_context(
            wallet=wallet_data,
            page='wallet',
        )

        return request.render('eth_agency_portal.portal_wallet', context)

    # ==================== Reservations ====================

    @http.route('/agency/bonus/reservations', type='http', auth='public', website=True)
    def portal_reservations(self, **kwargs):
        """Bonus reservations list"""
        if not self._check_login():
            return request.redirect('/agency/login')

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        # Get filters
        params = {
            'state': kwargs.get('state'),
            'date_from': kwargs.get('date_from'),
            'date_to': kwargs.get('date_to'),
            'limit': kwargs.get('limit', 20),
            'offset': kwargs.get('offset', 0),
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        # Get reservations from Travel API
        reservations_data = {'reservations': [], 'total_count': 0}
        result = api_client.get_bonus_reservations(token, params)
        if result.get('success') and result.get('data'):
            reservations_data = result['data']

        context = self._portal_context(
            reservations=reservations_data.get('reservations', []),
            total_count=reservations_data.get('total_count', 0),
            current_state=kwargs.get('state'),
            current_date_from=kwargs.get('date_from'),
            current_date_to=kwargs.get('date_to'),
            page='reservations',
        )

        return request.render('eth_agency_portal.portal_reservations', context)

    @http.route('/agency/bonus/reservations/<int:reservation_id>', type='http', auth='public', website=True)
    def portal_reservation_detail(self, reservation_id, **kwargs):
        """Single reservation detail"""
        if not self._check_login():
            return request.redirect('/agency/login')

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        # Get reservation from Travel API
        result = api_client.get_bonus_reservation(token, reservation_id)
        if not result.get('success') or not result.get('data'):
            return request.redirect('/agency/bonus/reservations')

        context = self._portal_context(
            reservation=result['data'],
            page='reservations',
        )

        return request.render('eth_agency_portal.portal_reservation_detail', context)

    @http.route('/agency/bonus/reservations/new', type='http', auth='public', website=True)
    def portal_reservation_new(self, **kwargs):
        """New reservation form"""
        if not self._check_login():
            return request.redirect('/agency/login')

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        # Get hotels and other data from Travel API
        hotels_result = api_client.get_agency_interested_hotels(token)
        hotels = hotels_result.get('data', []) if hotels_result.get('success') else []

        markets_result = api_client.get_markets()
        markets = markets_result.get('data', []) if markets_result.get('success') else []

        operators_result = api_client.get_operators()
        operators = operators_result.get('data', []) if operators_result.get('success') else []

        context = self._portal_context(
            hotels=hotels,
            markets=markets,
            operators=operators,
            error=kwargs.get('error'),
            page='reservations',
        )

        return request.render('eth_agency_portal.portal_reservation_form', context)

    @http.route('/agency/bonus/reservations/create', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def portal_reservation_create(self, **kwargs):
        """Create new reservation"""
        if not self._check_login():
            return request.redirect('/agency/login')

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        # Prepare reservation data
        data = {
            'hotel_id': int(kwargs.get('hotel_id')) if kwargs.get('hotel_id') else None,
            'checkin_date': kwargs.get('checkin_date'),
            'checkout_date': kwargs.get('checkout_date'),
            'guest_name': kwargs.get('guest_name'),
            'room_nights': int(kwargs.get('room_nights', 1)),
            'voucher_number': kwargs.get('voucher_number'),
            'notes': kwargs.get('notes'),
        }

        if kwargs.get('market_id'):
            data['market_id'] = int(kwargs.get('market_id'))
        if kwargs.get('operator_id'):
            data['operator_id'] = int(kwargs.get('operator_id'))

        # Validate required fields
        if not all([data.get('hotel_id'), data.get('checkin_date'), data.get('checkout_date'), data.get('guest_name')]):
            return request.redirect('/agency/bonus/reservations/new?error=missing_fields')

        # Create via Travel API
        result = api_client.create_bonus_reservation(token, data)
        if result.get('success') and result.get('data'):
            reservation_id = result['data'].get('id')
            return request.redirect(f'/agency/bonus/reservations/{reservation_id}')
        else:
            error = result.get('error', 'unknown')
            return request.redirect(f'/agency/bonus/reservations/new?error={error}')

    # ==================== Calculate Bonus ====================

    @http.route('/agency/bonus/calculate', type='json', auth='public', csrf=True)
    def portal_calculate_bonus(self, **kwargs):
        """Calculate bonus (AJAX endpoint)"""
        if not self._check_login():
            return {'success': False, 'error': 'Not authenticated'}

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        data = {
            'hotel_id': kwargs.get('hotel_id'),
            'market_id': kwargs.get('market_id'),
            'checkin_date': kwargs.get('checkin_date'),
            'checkout_date': kwargs.get('checkout_date'),
            'room_nights': kwargs.get('room_nights', 1),
        }

        result = api_client.calculate_bonus(token, data)
        return result

    # ==================== Contracts ====================

    @http.route('/agency/bonus/contracts', type='http', auth='public', website=True)
    def portal_contracts(self, **kwargs):
        """View available bonus contracts"""
        if not self._check_login():
            return request.redirect('/agency/login')

        api_client = request.env['travel.api.client'].sudo()
        token = self._get_agency_token()

        # Get contracts from Travel API
        params = {
            'hotel_id': kwargs.get('hotel_id'),
            'market_id': kwargs.get('market_id'),
        }
        params = {k: v for k, v in params.items() if v}

        result = api_client.get_bonus_contracts(token, params)
        contracts = result.get('data', []) if result.get('success') else []

        # Get interested hotels for filter
        hotels_result = api_client.get_agency_interested_hotels(token)
        hotels = hotels_result.get('data', []) if hotels_result.get('success') else []

        context = self._portal_context(
            contracts=contracts,
            hotels=hotels,
            current_hotel_id=kwargs.get('hotel_id'),
            page='contracts',
        )

        return request.render('eth_agency_portal.portal_contracts', context)
