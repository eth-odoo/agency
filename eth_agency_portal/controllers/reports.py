# -*- coding: utf-8 -*-
"""
Reports Controller - Agency Reports Page
"""
import logging
from datetime import datetime, timedelta
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase, require_auth, auto_language

_logger = logging.getLogger(__name__)


class AgencyReports(AgencyPortalBase):
    """Reports page controller"""

    # ==================== Main Reports Page ====================

    @http.route('/agency/reports', type='http', auth='public', website=True)
    @require_auth()
    @auto_language
    def reports_page(self, **kwargs):
        """Main reports page with 4 sections based on membership"""
        agency_data = self._get_agency_data()

        values = self._prepare_values(
            page_title=_('Reports'),
            has_tickets=agency_data.get('has_tickets', False) if agency_data else False,
            has_sales=agency_data.get('has_sales', False) if agency_data else False,
            has_bonus=agency_data.get('has_bonus', False) if agency_data else False,
            has_contract=self._has_contract_permission(agency_data),
        )

        return request.render('eth_agency_portal.portal_reports', values)

    def _has_contract_permission(self, agency_data):
        """Check if agency has contract/stop sales permission"""
        if not agency_data:
            return False
        purposes = agency_data.get('membership_purposes', [])
        return 'Contract' in purposes or 'Sözleşme' in purposes or 'Stop Sales' in purposes

    # ==================== Ticket Reports ====================

    @http.route('/agency/reports/tickets', type='http', auth='public', website=True)
    @require_auth()
    @auto_language
    def ticket_reports_page(self, **kwargs):
        """Ticket reports detail page"""
        values = self._prepare_values(
            page_title=_('Ticket Reports'),
        )
        return request.render('eth_agency_portal.portal_reports_tickets', values)

    @http.route('/agency/api/reports/tickets/summary', type='json', auth='public', methods=['POST'], csrf=False)
    def get_ticket_summary(self, date_from=None, date_to=None, **kwargs):
        """Get ticket sales summary from API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Not authenticated'}

            agency_id = self._get_agency_id()
            if not agency_id:
                return {'success': False, 'error': 'No agency found'}

            # Default date range: last 30 days
            if not date_from:
                date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not date_to:
                date_to = datetime.now().strftime('%Y-%m-%d')

            # Get orders from local database (eth_daily_inventory)
            Order = request.env['sale.order'].sudo()

            # Find agency partner
            agency = request.env['travel.agency'].sudo().browse(agency_id)
            partner_id = agency.partner_id.id if agency.partner_id else None

            if not partner_id:
                return {'success': False, 'error': 'Agency partner not found'}

            domain = [
                ('partner_id', '=', partner_id),
                ('date_order', '>=', date_from),
                ('date_order', '<=', date_to),
            ]

            # Check if ticket orders have specific field
            if 'is_ticket_order' in Order._fields:
                domain.append(('is_ticket_order', '=', True))

            orders = Order.search(domain, order='date_order desc')

            # Calculate summary
            total_orders = len(orders)
            total_amount = sum(orders.mapped('amount_total'))
            total_tickets = sum(orders.mapped('order_line.product_uom_qty'))

            # Group by state
            by_state = {}
            for order in orders:
                state = order.state
                if state not in by_state:
                    by_state[state] = {'count': 0, 'amount': 0}
                by_state[state]['count'] += 1
                by_state[state]['amount'] += order.amount_total

            # Group by product (ticket type)
            by_product = {}
            for order in orders:
                for line in order.order_line:
                    product_name = line.product_id.name
                    if product_name not in by_product:
                        by_product[product_name] = {'quantity': 0, 'amount': 0}
                    by_product[product_name]['quantity'] += line.product_uom_qty
                    by_product[product_name]['amount'] += line.price_subtotal

            # Recent orders
            recent_orders = []
            for order in orders[:10]:
                recent_orders.append({
                    'id': order.id,
                    'name': order.name,
                    'date': order.date_order.strftime('%Y-%m-%d %H:%M') if order.date_order else '',
                    'amount': order.amount_total,
                    'state': order.state,
                    'ticket_count': sum(order.order_line.mapped('product_uom_qty')),
                })

            return {
                'success': True,
                'data': {
                    'summary': {
                        'total_orders': total_orders,
                        'total_amount': total_amount,
                        'total_tickets': int(total_tickets),
                        'currency': orders[0].currency_id.symbol if orders else '€',
                    },
                    'by_state': by_state,
                    'by_product': by_product,
                    'recent_orders': recent_orders,
                    'date_from': date_from,
                    'date_to': date_to,
                }
            }

        except Exception as e:
            _logger.error(f"Error getting ticket summary: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== Bonus Reports ====================

    @http.route('/agency/reports/bonus', type='http', auth='public', website=True)
    @require_auth()
    @auto_language
    def bonus_reports_page(self, **kwargs):
        """Bonus reports detail page"""
        values = self._prepare_values(
            page_title=_('Bonus Reports'),
        )
        return request.render('eth_agency_portal.portal_reports_bonus', values)

    @http.route('/agency/api/reports/bonus/summary', type='json', auth='public', methods=['POST'], csrf=False)
    def get_bonus_summary(self, date_from=None, date_to=None, **kwargs):
        """Get bonus reservations summary from API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Not authenticated'}

            token = request.session.get('agency_token')

            # Default date range: last 30 days
            if not date_from:
                date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not date_to:
                date_to = datetime.now().strftime('%Y-%m-%d')

            # Call Travel API for bonus summary
            api_client = request.env['travel.api.client'].sudo()

            # Get bonus wallet
            wallet_result = api_client.get_bonus_wallet(token)
            wallet_data = wallet_result.get('data', {}) if wallet_result.get('success') else {}

            # Get bonus reservations
            reservations_result = api_client.get_bonus_reservations(token, {
                'date_from': date_from,
                'date_to': date_to,
            })

            reservations = reservations_result.get('data', []) if reservations_result.get('success') else []

            # Calculate summary
            total_reservations = len(reservations)
            total_bonus = sum(r.get('bonus_amount', 0) for r in reservations)

            # Group by state
            by_state = {}
            for res in reservations:
                state = res.get('state', 'unknown')
                if state not in by_state:
                    by_state[state] = {'count': 0, 'bonus': 0}
                by_state[state]['count'] += 1
                by_state[state]['bonus'] += res.get('bonus_amount', 0)

            # Group by hotel
            by_hotel = {}
            for res in reservations:
                hotel = res.get('hotel_name', 'Unknown')
                if hotel not in by_hotel:
                    by_hotel[hotel] = {'count': 0, 'bonus': 0, 'nights': 0}
                by_hotel[hotel]['count'] += 1
                by_hotel[hotel]['bonus'] += res.get('bonus_amount', 0)
                by_hotel[hotel]['nights'] += res.get('room_nights', 0)

            # Recent reservations
            recent = reservations[:10] if isinstance(reservations, list) else []

            return {
                'success': True,
                'data': {
                    'wallet': wallet_data,
                    'summary': {
                        'total_reservations': total_reservations,
                        'total_bonus': total_bonus,
                        'currency': wallet_data.get('currency', 'EUR'),
                    },
                    'by_state': by_state,
                    'by_hotel': by_hotel,
                    'recent_reservations': recent,
                    'date_from': date_from,
                    'date_to': date_to,
                }
            }

        except Exception as e:
            _logger.error(f"Error getting bonus summary: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== Hotel Booking Reports ====================

    @http.route('/agency/reports/bookings', type='http', auth='public', website=True)
    @require_auth()
    @auto_language
    def booking_reports_page(self, **kwargs):
        """Hotel booking reports detail page"""
        values = self._prepare_values(
            page_title=_('Hotel Booking Reports'),
        )
        return request.render('eth_agency_portal.portal_reports_bookings', values)

    @http.route('/agency/api/reports/bookings/summary', type='json', auth='public', methods=['POST'], csrf=False)
    def get_booking_summary(self, date_from=None, date_to=None, **kwargs):
        """Get hotel bookings summary from API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Not authenticated'}

            token = request.session.get('agency_token')

            # Default date range: last 30 days
            if not date_from:
                date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not date_to:
                date_to = datetime.now().strftime('%Y-%m-%d')

            # Call Travel API for bookings
            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_hotel_bookings(token, {
                'date_from': date_from,
                'date_to': date_to,
            })

            bookings = result.get('data', []) if result.get('success') else []

            # Calculate summary
            total_bookings = len(bookings)
            total_amount = sum(b.get('total_amount', 0) for b in bookings)
            total_nights = sum(b.get('nights', 0) for b in bookings)

            # Group by state
            by_state = {}
            for booking in bookings:
                state = booking.get('state', 'unknown')
                if state not in by_state:
                    by_state[state] = {'count': 0, 'amount': 0}
                by_state[state]['count'] += 1
                by_state[state]['amount'] += booking.get('total_amount', 0)

            # Group by hotel
            by_hotel = {}
            for booking in bookings:
                hotel = booking.get('hotel_name', 'Unknown')
                if hotel not in by_hotel:
                    by_hotel[hotel] = {'count': 0, 'amount': 0, 'nights': 0}
                by_hotel[hotel]['count'] += 1
                by_hotel[hotel]['amount'] += booking.get('total_amount', 0)
                by_hotel[hotel]['nights'] += booking.get('nights', 0)

            # Recent bookings
            recent = bookings[:10] if isinstance(bookings, list) else []

            return {
                'success': True,
                'data': {
                    'summary': {
                        'total_bookings': total_bookings,
                        'total_amount': total_amount,
                        'total_nights': total_nights,
                        'currency': 'EUR',
                    },
                    'by_state': by_state,
                    'by_hotel': by_hotel,
                    'recent_bookings': recent,
                    'date_from': date_from,
                    'date_to': date_to,
                }
            }

        except Exception as e:
            _logger.error(f"Error getting booking summary: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== Stop Sales Reports ====================

    @http.route('/agency/reports/stop-sales', type='http', auth='public', website=True)
    @require_auth()
    @auto_language
    def stop_sales_reports_page(self, **kwargs):
        """Stop sales reports detail page"""
        values = self._prepare_values(
            page_title=_('Stop Sales Reports'),
        )
        return request.render('eth_agency_portal.portal_reports_stop_sales', values)

    @http.route('/agency/api/reports/stop-sales/summary', type='json', auth='public', methods=['POST'], csrf=False)
    def get_stop_sales_summary(self, date_from=None, date_to=None, **kwargs):
        """Get stop sales summary"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Not authenticated'}

            token = request.session.get('agency_token')
            agency_id = self._get_agency_id()

            # Default date range: next 30 days for stop sales
            if not date_from:
                date_from = datetime.now().strftime('%Y-%m-%d')
            if not date_to:
                date_to = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

            # Check if stop sales model exists in local database
            StopSales = request.env.get('hotel.stop.sales')

            if StopSales is None:
                # Try travel.stop.sales
                StopSales = request.env.get('travel.stop.sales')

            if StopSales is None:
                return {
                    'success': True,
                    'data': {
                        'summary': {
                            'total_stop_sales': 0,
                            'active_stop_sales': 0,
                        },
                        'by_hotel': {},
                        'recent_stop_sales': [],
                        'date_from': date_from,
                        'date_to': date_to,
                        'message': 'Stop Sales module not installed'
                    }
                }

            # Get agency's interested hotels
            agency = request.env['travel.agency'].sudo().browse(agency_id)
            hotel_ids = []
            if hasattr(agency, 'interested_hotel_ids') and agency.interested_hotel_ids:
                hotel_ids = agency.interested_hotel_ids.ids

            # Query stop sales
            domain = [
                ('date_from', '<=', date_to),
                ('date_to', '>=', date_from),
            ]
            if hotel_ids:
                domain.append(('hotel_id', 'in', hotel_ids))

            stop_sales = StopSales.sudo().search(domain, order='date_from desc')

            # Calculate summary
            total_stop_sales = len(stop_sales)
            active_stop_sales = len(stop_sales.filtered(lambda s: s.state == 'active' if hasattr(s, 'state') else True))

            # Group by hotel
            by_hotel = {}
            for ss in stop_sales:
                hotel_name = ss.hotel_id.name if ss.hotel_id else 'Unknown'
                if hotel_name not in by_hotel:
                    by_hotel[hotel_name] = {'count': 0, 'days': 0}
                by_hotel[hotel_name]['count'] += 1
                # Calculate days
                if ss.date_from and ss.date_to:
                    days = (ss.date_to - ss.date_from).days + 1
                    by_hotel[hotel_name]['days'] += days

            # Recent stop sales
            recent = []
            for ss in stop_sales[:10]:
                recent.append({
                    'id': ss.id,
                    'hotel_name': ss.hotel_id.name if ss.hotel_id else 'Unknown',
                    'date_from': ss.date_from.strftime('%Y-%m-%d') if ss.date_from else '',
                    'date_to': ss.date_to.strftime('%Y-%m-%d') if ss.date_to else '',
                    'room_type': ss.room_type_id.name if hasattr(ss, 'room_type_id') and ss.room_type_id else 'All',
                    'reason': ss.reason if hasattr(ss, 'reason') else '',
                })

            return {
                'success': True,
                'data': {
                    'summary': {
                        'total_stop_sales': total_stop_sales,
                        'active_stop_sales': active_stop_sales,
                    },
                    'by_hotel': by_hotel,
                    'recent_stop_sales': recent,
                    'date_from': date_from,
                    'date_to': date_to,
                }
            }

        except Exception as e:
            _logger.error(f"Error getting stop sales summary: {str(e)}")
            return {'success': False, 'error': str(e)}
