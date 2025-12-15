# -*- coding: utf-8 -*-
"""
Visitor Management Controller for Agency Portal
Handles visitor/guest information for ticket sales
"""
import logging
from odoo import http
from odoo.http import request
from .base import AgencyPortalBase

_logger = logging.getLogger(__name__)


class AgencyVisitorController(AgencyPortalBase):
    """Visitor management for agency ticket sales"""

    def _get_visitors_key(self):
        """Get session key for visitors"""
        agency_data = self._get_agency_data()
        agency_id = agency_data.get('id', 0) if agency_data else 0
        return f'ticket_visitors_{agency_id}'

    def _get_visitors(self):
        """Get visitors from session"""
        return request.session.get(self._get_visitors_key(), [])

    def _save_visitors(self, visitors):
        """Save visitors to session"""
        request.session[self._get_visitors_key()] = visitors

    def _clear_visitors(self):
        """Clear visitors from session"""
        request.session.pop(self._get_visitors_key(), None)

    def _get_cart_key(self):
        """Get session key for ticket cart"""
        agency_data = self._get_agency_data()
        agency_id = agency_data.get('id', 0) if agency_data else 0
        return f'ticket_cart_{agency_id}'

    def _get_cart(self):
        """Get cart from session"""
        return request.session.get(self._get_cart_key(), {'lines': [], 'visit_date': None, 'total': 0})

    def _delete_unused_visitors(self):
        """Deletes visitors whose index exceeds current cart quantity.
        Only removes excess visitors when quantity is reduced.
        """
        cart = self._get_cart()
        visitors = self._get_visitors()

        _logger.info(f"_delete_unused_visitors - Cart: {cart}")
        _logger.info(f"_delete_unused_visitors - Visitors before: {visitors}")

        # Build dict of variant_id (as string) -> quantity from cart
        cart_quantities = {}
        for line in cart.get('lines', []):
            variant_id = line.get('variant_id') or line.get('product_id')
            if variant_id:
                # Convert to string for consistent comparison with JS data
                cart_quantities[str(variant_id)] = line.get('quantity', 0)

        _logger.info(f"_delete_unused_visitors - cart_quantities: {cart_quantities}")

        # Keep visitors whose index is within the cart quantity
        updated_visitors = []
        for visitor in visitors:
            # Convert variant_id to string for comparison
            variant_id = str(visitor.get('variant_id', ''))
            visitor_index = visitor.get('visitor_index', 0)
            max_quantity = cart_quantities.get(variant_id, 0)

            _logger.info(f"_delete_unused_visitors - Checking visitor: variant_id={variant_id}, index={visitor_index}, max_qty={max_quantity}")

            # Keep if variant still in cart AND visitor_index <= quantity
            if variant_id in cart_quantities and visitor_index <= max_quantity:
                updated_visitors.append(visitor)
                _logger.info(f"_delete_unused_visitors - KEEPING visitor")
            else:
                _logger.info(f"_delete_unused_visitors - REMOVING visitor")

        _logger.info(f"_delete_unused_visitors - Visitors after: {updated_visitors}")

        self._save_visitors(updated_visitors)
        return updated_visitors

    @http.route('/agency/api/tickets/visitors/test', type='json', auth='public', methods=['POST'], csrf=False)
    def test_visitors_endpoint(self, **kw):
        """Test endpoint to verify routing works"""
        _logger.info("=== VISITORS TEST ENDPOINT CALLED ===")
        return {'success': True, 'message': 'Visitors endpoint is working!'}

    @http.route('/agency/api/tickets/visitors/update', type='json', auth='public', methods=['POST'], csrf=False)
    def update_visitors(self, **kw):
        """Update visitors section"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            _logger.info("=== AGENCY UPDATE VISITORS CALLED ===")

            self._delete_unused_visitors()
            cart = self._get_cart()
            visitors = self._get_visitors()

            _logger.info(f"Cart: {cart}")
            _logger.info(f"Visitors: {visitors}")

            return {'success': True, 'cart': cart, 'visitors': visitors}

        except Exception as e:
            _logger.error(f"Error in update_visitors: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/visitors/save', type='json', auth='public', methods=['POST'], csrf=False)
    def save_visitor(self, visitor_data=None, **kw):
        """Save visitor information"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not visitor_data:
                return {'success': False, 'error': 'No visitor data provided'}

            _logger.info(f"Saving visitor: {visitor_data}")

            visitors = self._get_visitors()

            variant_id = visitor_data.get('variant_id')
            visitor_index = visitor_data.get('visitor_index')

            existing_index = None
            for i, v in enumerate(visitors):
                if v.get('variant_id') == variant_id and v.get('visitor_index') == visitor_index:
                    existing_index = i
                    break

            visitor_record = {
                'variant_id': variant_id,
                'product_name': visitor_data.get('product_name', ''),
                'visitor_index': visitor_index,
                'ticket_product_type': visitor_data.get('ticket_product_type', 'adult'),
                'first_name': visitor_data.get('first_name', ''),
                'last_name': visitor_data.get('last_name', ''),
                'phone': visitor_data.get('phone', ''),
                'email': visitor_data.get('email', ''),
                'identity': visitor_data.get('identity', ''),
            }

            if existing_index is not None:
                visitors[existing_index] = visitor_record
            else:
                visitors.append(visitor_record)

            self._save_visitors(visitors)

            return {'success': True, 'visitor': visitor_record}

        except Exception as e:
            _logger.error(f"Error saving visitor: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/visitors/get', type='json', auth='public', methods=['POST'], csrf=False)
    def get_all_visitors(self, **kw):
        """Get all visitors for current cart"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            visitors = self._get_visitors()
            return {'success': True, 'visitors': visitors}

        except Exception as e:
            _logger.error(f"Error getting visitors: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/visitors/check', type='json', auth='public', methods=['POST'], csrf=False)
    def check_visitors_complete(self, **kw):
        """Check if all visitors are filled"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            cart = self._get_cart()
            visitors = self._get_visitors()

            required_visitors = {}
            for line in cart.get('lines', []):
                variant_id = line.get('variant_id') or line.get('product_id')
                ticket_type = line.get('ticket_product_type', '')
                if ticket_type in ['adult', 'child']:
                    required_visitors[variant_id] = line.get('quantity', 0)

            existing_visitors = {}
            for visitor in visitors:
                variant_id = visitor.get('variant_id')
                if variant_id in required_visitors:
                    existing_visitors[variant_id] = existing_visitors.get(variant_id, 0) + 1

            for variant_id, required_count in required_visitors.items():
                existing_count = existing_visitors.get(variant_id, 0)
                if existing_count < required_count:
                    missing_count = required_count - existing_count
                    return {
                        'success': True,
                        'complete': False,
                        'message': f'Please fill in the information for {missing_count} more visitor(s).'
                    }

            return {'success': True, 'complete': True}

        except Exception as e:
            _logger.error(f"Error checking visitors: {str(e)}")
            return {'success': False, 'error': str(e)}
