# -*- coding: utf-8 -*-
"""
Ticket Sales Controller for Agency Portal
Communicates with Ticket API to manage ticket sales
"""
import logging
from datetime import datetime
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase

_logger = logging.getLogger(__name__)


class TicketSalesController(AgencyPortalBase):
    """Ticket sales management controllers using Ticket API"""

    def _get_cart_key(self):
        """Get session key for ticket cart"""
        agency_data = self._get_agency_data()
        agency_id = agency_data.get('id', 0) if agency_data else 0
        return f'ticket_cart_{agency_id}'

    def _get_cart(self):
        """Get cart from session"""
        return request.session.get(self._get_cart_key(), {'lines': [], 'visit_date': None, 'total': 0})

    def _save_cart(self, cart):
        """Save cart to session"""
        request.session[self._get_cart_key()] = cart

    def _clear_cart(self):
        """Clear cart from session"""
        request.session.pop(self._get_cart_key(), None)

    # ==================== Visitor Helper Methods ====================

    def _get_visitors_key(self):
        """Get session key for visitors"""
        agency_data = self._get_agency_data()
        agency_id = agency_data.get('id', 0) if agency_data else 0
        return f'ticket_visitors_{agency_id}'

    def _clear_visitors(self):
        """Clear visitors from session"""
        request.session.pop(self._get_visitors_key(), None)

    def _delete_unused_visitors(self):
        """Deletes visitors whose index exceeds current cart quantity.
        Only removes excess visitors when quantity is reduced.
        """
        cart = self._get_cart()
        visitors = request.session.get(self._get_visitors_key(), [])

        _logger.info(f"_delete_unused_visitors (ticket_sales) - Cart: {cart}")
        _logger.info(f"_delete_unused_visitors (ticket_sales) - Visitors before: {visitors}")

        # Build dict of variant_id (as string) -> quantity from cart
        cart_quantities = {}
        for line in cart.get('lines', []):
            variant_id = line.get('variant_id') or line.get('product_id')
            if variant_id:
                # Convert to string for consistent comparison with JS data
                cart_quantities[str(variant_id)] = line.get('quantity', 0)

        _logger.info(f"_delete_unused_visitors (ticket_sales) - cart_quantities: {cart_quantities}")

        # Keep visitors whose index is within the cart quantity
        updated_visitors = []
        for visitor in visitors:
            # Convert variant_id to string for comparison
            variant_id = str(visitor.get('variant_id', ''))
            visitor_index = visitor.get('visitor_index', 0)
            max_quantity = cart_quantities.get(variant_id, 0)

            _logger.info(f"_delete_unused_visitors (ticket_sales) - Checking visitor: variant_id={variant_id}, index={visitor_index}, max_qty={max_quantity}")

            # Keep if variant still in cart AND visitor_index <= quantity
            if variant_id in cart_quantities and visitor_index <= max_quantity:
                updated_visitors.append(visitor)
                _logger.info(f"_delete_unused_visitors (ticket_sales) - KEEPING visitor")
            else:
                _logger.info(f"_delete_unused_visitors (ticket_sales) - REMOVING visitor")

        _logger.info(f"_delete_unused_visitors (ticket_sales) - Visitors after: {updated_visitors}")

        request.session[self._get_visitors_key()] = updated_visitors
        return updated_visitors

    # ==================== Main Page ====================

    @http.route('/agency/tickets', type='http', auth="public", website=True, csrf=False)
    def ticket_sales_page(self, **kw):
        """Main ticket sales page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            user_data = self._get_current_user()
            agency_data = self._get_agency_data()

            # Check if agency has Tickets purpose
            if not agency_data or not agency_data.get('has_tickets', False):
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='tickets',
                        message=_('Your agency does not have Ticket Sales membership. Please contact administrator.')
                    ))

            # Check permissions
            permissions = user_data.get('permissions', {}) if user_data else {}
            can_manage = permissions.get('can_manage_bookings', True) if permissions else True

            if not can_manage:
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='tickets',
                        message=_('You do not have permission to manage ticket sales.')
                    ))

            # Get current cart
            cart = self._get_cart()

            values = self._prepare_values(
                page_name='tickets',
                cart=cart
            )
            return request.render('eth_agency_portal.agency_ticket_sales', values)

        except Exception as e:
            _logger.error(f"Error in ticket sales page: {str(e)}", exc_info=True)
            return request.redirect('/agency/dashboard')

    # ==================== API Endpoints ====================

    @http.route('/agency/api/tickets/types', type='json', auth='public', methods=['POST'], csrf=False)
    def get_ticket_types(self, **kw):
        """Get available ticket types"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_ticket_types()

            if result.get('success'):
                return {'success': True, 'data': result.get('ticket_types', [])}
            else:
                # Return default types if API fails
                return {
                    'success': True,
                    'data': [
                        {'code': 'park', 'name': 'Theme Park'},
                        {'code': 'parkevening', 'name': 'Theme Park Evening'},
                        {'code': 'event', 'name': 'Event'},
                    ]
                }

        except Exception as e:
            _logger.error(f"Error getting ticket types: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/products', type='json', auth='public', methods=['POST'], csrf=False)
    def get_products(self, ticket_type=None, visit_date=None, **kw):
        """Get ticket products from Ticket API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_ticket_products(
                ticket_type=ticket_type,
                currency='EUR',
                visit_date=visit_date
            )

            if result.get('success'):
                return {
                    'success': True,
                    'data': {
                        'products': result.get('products', []),
                        'count': result.get('count', 0)
                    }
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get products')}

        except Exception as e:
            _logger.error(f"Error getting products: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/stock', type='json', auth='public', methods=['POST'], csrf=False)
    def get_stock(self, product_id=None, visit_date=None, **kw):
        """Get stock for a product on specific date"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not product_id or not visit_date:
                return {'success': False, 'error': 'product_id and visit_date are required'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_ticket_stock(product_id, visit_date)

            if result.get('success'):
                return {
                    'success': True,
                    'data': {
                        'available_stock': result.get('available_stock', 0),
                        'total_stock': result.get('total_stock', 0)
                    }
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get stock')}

        except Exception as e:
            _logger.error(f"Error getting stock: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/cart/add', type='json', auth='public', methods=['POST'], csrf=False)
    def add_to_cart(self, product_id=None, product_name=None, quantity=1, price=0, visit_date=None, variant_id=None, ticket_product_type=None, **kw):
        """Add product to cart"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            cart = self._get_cart()

            # Update visit date
            if visit_date:
                # If visit date changed, clear cart and visitors
                if cart.get('visit_date') and cart.get('visit_date') != visit_date and cart.get('lines'):
                    cart = {'lines': [], 'visit_date': visit_date, 'total': 0}
                    self._clear_visitors()
                cart['visit_date'] = visit_date

            # Use variant_id if provided, otherwise use product_id
            item_id = variant_id or product_id

            # Check if product already in cart
            existing_line = None
            for line in cart.get('lines', []):
                if line.get('variant_id') == item_id or line.get('product_id') == item_id:
                    existing_line = line
                    break

            if existing_line:
                if quantity <= 0:
                    # Remove from cart
                    cart['lines'] = [l for l in cart['lines'] if not (l.get('variant_id') == item_id or l.get('product_id') == item_id)]
                else:
                    existing_line['quantity'] = quantity
                    existing_line['price'] = price
                    if ticket_product_type:
                        existing_line['ticket_product_type'] = ticket_product_type
            else:
                if quantity > 0:
                    cart.setdefault('lines', []).append({
                        'product_id': product_id,
                        'variant_id': variant_id or product_id,
                        'product_name': product_name,
                        'quantity': quantity,
                        'price': price,
                        'ticket_product_type': ticket_product_type or '',
                    })

            # Calculate total
            cart['total'] = sum(l['quantity'] * l['price'] for l in cart['lines'])
            cart['item_count'] = sum(l['quantity'] for l in cart['lines'])

            self._save_cart(cart)

            # Get current visitors (don't delete any - let JS handle visitor management)
            visitors = request.session.get(self._get_visitors_key(), [])

            return {'success': True, 'cart': cart, 'visitors': visitors}

        except Exception as e:
            _logger.error(f"Error adding to cart: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/cart/get', type='json', auth='public', methods=['POST'], csrf=False)
    def get_cart(self, **kw):
        """Get current cart"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            cart = self._get_cart()
            return {'success': True, 'cart': cart}

        except Exception as e:
            _logger.error(f"Error getting cart: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/cart/clear', type='json', auth='public', methods=['POST'], csrf=False)
    def clear_cart(self, **kw):
        """Clear cart"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            self._clear_cart()
            return {'success': True}

        except Exception as e:
            _logger.error(f"Error clearing cart: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/order/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_order(self, **kw):
        """Create ticket order"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            cart = self._get_cart()
            if not cart.get('lines'):
                return {'success': False, 'error': 'Cart is empty'}

            if not cart.get('visit_date'):
                return {'success': False, 'error': 'Please select a visit date'}

            # Use agency partner_id for ticket system
            partner_id = agency_data.get('partner_id', 1)

            # Prepare order lines
            lines = [
                {
                    'product_id': line['variant_id'] or line['product_id'],
                    'quantity': line['quantity'],
                    'price_unit': line['price'],
                }
                for line in cart['lines']
            ]

            # Generate agency reference
            agency_ref = f"AGENCY_{agency_data['id']}_{int(datetime.now().timestamp())}"

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.create_ticket_order(
                partner_id=partner_id,
                visit_date=cart['visit_date'],
                lines=lines,
                agency_ref=agency_ref
            )

            if result.get('success'):
                # Clear cart after successful order
                self._clear_cart()

                return {
                    'success': True,
                    'data': {
                        'order_id': result.get('order_id'),
                        'order_name': result.get('order_name'),
                        'amount_total': result.get('amount_total')
                    }
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to create order')}

        except Exception as e:
            _logger.error(f"Error creating order: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/orders', type='json', auth='public', methods=['POST'], csrf=False)
    def get_orders(self, **kw):
        """Get ticket orders for agency"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            # For now, return empty list - orders are stored in ticket system
            # This could be enhanced to store local references
            return {
                'success': True,
                'data': {
                    'orders': [],
                    'total_count': 0
                }
            }

        except Exception as e:
            _logger.error(f"Error getting orders: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/order/<int:order_id>', type='json', auth='public', methods=['POST'], csrf=False)
    def get_order_detail(self, order_id, **kw):
        """Get order detail"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_ticket_order(order_id)

            if result.get('success'):
                return {'success': True, 'data': result.get('order', {})}
            else:
                return {'success': False, 'error': result.get('error', 'Order not found')}

        except Exception as e:
            _logger.error(f"Error getting order detail: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/order/<int:order_id>/confirm', type='json', auth='public', methods=['POST'], csrf=False)
    def confirm_order(self, order_id, **kw):
        """Confirm ticket order"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.confirm_ticket_order(order_id)

            if result.get('success'):
                return {'success': True, 'message': 'Order confirmed successfully'}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to confirm order')}

        except Exception as e:
            _logger.error(f"Error confirming order: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/order/<int:order_id>/cancel', type='json', auth='public', methods=['POST'], csrf=False)
    def cancel_order(self, order_id, **kw):
        """Cancel ticket order"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.cancel_ticket_order(order_id)

            if result.get('success'):
                return {'success': True, 'message': 'Order cancelled successfully'}
            else:
                return {'success': False, 'error': result.get('error', 'Failed to cancel order')}

        except Exception as e:
            _logger.error(f"Error cancelling order: {str(e)}")
            return {'success': False, 'error': str(e)}
