# -*- coding: utf-8 -*-
"""
Checkout Controller for Agency Portal
Handles billing address, payment selection, and order creation
"""
import copy
import logging
from datetime import datetime
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase

_logger = logging.getLogger(__name__)


class CheckoutController(AgencyPortalBase):
    """Checkout flow controllers"""

    def _get_checkout_key(self):
        """Get session key for checkout data"""
        agency_data = self._get_agency_data()
        agency_id = agency_data.get('id', 0) if agency_data else 0
        return f'ticket_checkout_{agency_id}'

    def _get_checkout_data(self):
        """Get checkout data from session"""
        key = self._get_checkout_key()
        data = request.session.get(key, {})
        _logger.info(f"[CHECKOUT-GET] key={key}, has_billing={bool(data.get('billing_address'))}, keys={list(data.keys())}")
        return data

    def _save_checkout_data(self, data):
        """Save checkout data to session"""
        # Deep copy to ensure session detects change
        data_copy = copy.deepcopy(data)
        key = self._get_checkout_key()
        request.session[key] = data_copy
        request.session.modified = True
        _logger.info(f"[CHECKOUT-SAVE] key={key}, has_billing={bool(data_copy.get('billing_address'))}, keys={list(data_copy.keys())}")

    def _clear_checkout_data(self):
        """Clear checkout data from session"""
        request.session.pop(self._get_checkout_key(), None)

    def _get_cart_key(self):
        """Get session key for ticket cart"""
        agency_data = self._get_agency_data()
        agency_id = agency_data.get('id', 0) if agency_data else 0
        return f'ticket_cart_{agency_id}'

    def _get_cart(self):
        """Get cart from session"""
        return request.session.get(self._get_cart_key(), {'lines': [], 'visit_date': None, 'total': 0})

    def _clear_cart(self):
        """Clear cart from session"""
        request.session.pop(self._get_cart_key(), None)

    def _get_visitors_key(self):
        """Get session key for visitors"""
        agency_data = self._get_agency_data()
        agency_id = agency_data.get('id', 0) if agency_data else 0
        return f'ticket_visitors_{agency_id}'

    def _get_visitors(self):
        """Get visitors from session"""
        return request.session.get(self._get_visitors_key(), [])

    def _clear_visitors(self):
        """Clear visitors from session"""
        request.session.pop(self._get_visitors_key(), None)

    # ==================== API Endpoints ====================

    @http.route('/agency/api/tickets/checkout/prepare', type='json', auth='public', methods=['POST'], csrf=False)
    def prepare_checkout(self, cart=None, visitors=None, **kw):
        """Prepare checkout - save cart and visitors to session"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not cart or not cart.get('lines'):
                return {'success': False, 'error': 'Cart is empty'}

            # Save cart and visitors to checkout session
            checkout_data = {
                'cart': cart,
                'visitors': visitors or [],
                'prepared_at': datetime.now().isoformat()
            }
            self._save_checkout_data(checkout_data)

            return {'success': True}

        except Exception as e:
            _logger.error(f"Error preparing checkout: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== Billing Address Page ====================

    @http.route('/agency/tickets/checkout/billing', type='http', auth="public", website=True, csrf=False)
    def billing_address_page(self, **kw):
        """Billing address page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            checkout_data = self._get_checkout_data()
            if not checkout_data or not checkout_data.get('cart', {}).get('lines'):
                return request.redirect('/agency/tickets')

            cart = checkout_data.get('cart', {})
            visitors = checkout_data.get('visitors', [])

            # Get countries for dropdown
            countries = request.env['res.country'].sudo().search([], order='name')

            values = self._prepare_values(
                page_name='checkout_billing',
                cart=cart,
                visitors=visitors,
                countries=countries,
                billing_address=checkout_data.get('billing_address', {})
            )
            return request.render('eth_agency_portal.agency_checkout_billing', values)

        except Exception as e:
            _logger.error(f"Error in billing address page: {str(e)}", exc_info=True)
            return request.redirect('/agency/tickets')

    @http.route('/agency/api/tickets/checkout/states', type='json', auth='public', methods=['POST'], csrf=False)
    def get_states(self, country_id=None, **kw):
        """Get states/cities for a country"""
        try:
            if not country_id:
                return {'success': False, 'error': 'Country ID required'}

            states = request.env['res.country.state'].sudo().search([
                ('country_id', '=', int(country_id))
            ], order='name')

            state_list = [{'id': s.id, 'name': s.name, 'code': s.code} for s in states]

            return {'success': True, 'states': state_list}

        except Exception as e:
            _logger.error(f"Error getting states: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/tickets/checkout/billing/save', type='json', auth='public', methods=['POST'], csrf=False)
    def save_billing_address(self, billing_data=None, **kw):
        """Save billing address"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            if not billing_data:
                return {'success': False, 'error': 'No billing data provided'}

            checkout_data = self._get_checkout_data()
            if not checkout_data:
                return {'success': False, 'error': 'Checkout session expired'}

            checkout_data['billing_address'] = billing_data
            self._save_checkout_data(checkout_data)

            return {'success': True}

        except Exception as e:
            _logger.error(f"Error saving billing address: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== Payment Page ====================

    @http.route('/agency/tickets/checkout/payment', type='http', auth="public", website=True, csrf=False)
    def payment_page(self, **kw):
        """Payment method selection page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            checkout_data = self._get_checkout_data()
            if not checkout_data or not checkout_data.get('cart', {}).get('lines'):
                return request.redirect('/agency/tickets')

            # Note: billing_address check removed - frontend uses localStorage
            # if not checkout_data.get('billing_address'):
            #     return request.redirect('/agency/tickets/checkout/billing')

            cart = checkout_data.get('cart', {})
            visitors = checkout_data.get('visitors', [])
            billing_address = checkout_data.get('billing_address', {})

            # Get available payment providers (check if payment module is installed)
            payment_providers = []
            try:
                if 'payment.provider' in request.env:
                    payment_providers = request.env['payment.provider'].sudo().search([
                        ('state', '=', 'enabled'),
                        ('is_published', '=', True)
                    ])
            except Exception as e:
                _logger.warning(f"Payment module not available: {str(e)}")

            values = self._prepare_values(
                page_name='checkout_payment',
                cart=cart,
                visitors=visitors,
                billing_address=billing_address,
                payment_providers=payment_providers
            )
            return request.render('eth_agency_portal.agency_checkout_payment', values)

        except Exception as e:
            _logger.error(f"Error in payment page: {str(e)}", exc_info=True)
            return request.redirect('/agency/tickets')

    # ==================== Bank Transfer (Havale) ====================

    @http.route('/agency/api/tickets/checkout/bank-transfer', type='json', auth='public', methods=['POST'], csrf=False)
    def process_bank_transfer(self, billing_data=None, **kw):
        """Process bank transfer order"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            checkout_data = self._get_checkout_data()
            if not checkout_data:
                return {'success': False, 'error': 'Checkout session expired'}

            cart = checkout_data.get('cart', {})
            visitors = checkout_data.get('visitors', [])
            # Use billing_data from frontend if provided (localStorage), fallback to session
            billing_address = billing_data if billing_data else checkout_data.get('billing_address', {})

            if not cart.get('lines'):
                return {'success': False, 'error': 'Cart is empty'}

            # Create or find partner from billing address
            partner = self._get_or_create_partner(billing_address, agency_data)

            # Create the sale order
            order = self._create_sale_order(cart, partner, agency_data, 'bank_transfer')

            if not order:
                return {'success': False, 'error': 'Failed to create order'}

            # Save visitors to order (as order notes or custom field)
            self._save_order_visitors(order, visitors)

            # Update inventory (reserve stock for bank transfer - will be confirmed when payment received)
            # Note: For bank transfer, we reserve stock immediately but order stays in draft until payment
            self._update_inventory(cart)

            # Clear checkout session
            self._clear_checkout_data()
            self._clear_cart()
            self._clear_visitors()

            return {
                'success': True,
                'order_id': order.id,
                'order_name': order.name,
                'amount_total': order.amount_total,
                'payment_method': 'bank_transfer'
            }

        except Exception as e:
            _logger.error(f"Error processing bank transfer: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== Credit Card Payment ====================

    @http.route('/agency/api/tickets/checkout/credit-card', type='json', auth='public', methods=['POST'], csrf=False)
    def process_credit_card(self, provider_id=None, billing_data=None, **kw):
        """Initialize credit card payment"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            checkout_data = self._get_checkout_data()
            if not checkout_data:
                return {'success': False, 'error': 'Checkout session expired'}

            cart = checkout_data.get('cart', {})
            visitors = checkout_data.get('visitors', [])
            # Use billing_data from frontend if provided (localStorage), fallback to session
            billing_address = billing_data if billing_data else checkout_data.get('billing_address', {})

            if not cart.get('lines'):
                return {'success': False, 'error': 'Cart is empty'}

            if not provider_id:
                return {'success': False, 'error': 'Payment provider not selected'}

            # Create or find partner from billing address
            partner = self._get_or_create_partner(billing_address, agency_data)

            # Create the sale order
            order = self._create_sale_order(cart, partner, agency_data, 'credit_card')

            if not order:
                return {'success': False, 'error': 'Failed to create order'}

            # Save visitors to order
            self._save_order_visitors(order, visitors)

            # Update inventory
            self._update_inventory(cart)

            # Get payment provider
            provider = request.env['payment.provider'].sudo().browse(int(provider_id))
            if not provider.exists():
                return {'success': False, 'error': 'Invalid payment provider'}

            # Create payment transaction
            transaction = self._create_payment_transaction(order, provider)

            # Clear checkout session
            self._clear_checkout_data()
            self._clear_cart()
            self._clear_visitors()

            return {
                'success': True,
                'order_id': order.id,
                'order_name': order.name,
                'amount_total': order.amount_total,
                'transaction_id': transaction.id if transaction else None,
                'payment_url': f'/agency/tickets/checkout/pay/{order.id}'
            }

        except Exception as e:
            _logger.error(f"Error processing credit card: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== Helper Methods ====================

    def _get_or_create_partner(self, billing_address, agency_data):
        """Get or create partner from billing address"""
        Partner = request.env['res.partner'].sudo()

        # Check if partner exists by email
        email = billing_address.get('email')
        if email:
            partner = Partner.search([('email', '=', email)], limit=1)
            if partner:
                # Update partner info
                update_vals = {
                    'name': billing_address.get('name') or partner.name,
                    'phone': billing_address.get('phone') or partner.phone,
                    'street': billing_address.get('street') or partner.street,
                    'city': billing_address.get('city') or partner.city,
                }
                # Add district to street2 if provided
                district = billing_address.get('district')
                if district:
                    update_vals['street2'] = district

                partner.write(update_vals)
                return partner

        # Create new partner
        country_id = billing_address.get('country_id')
        state_id = billing_address.get('state_id')
        district = billing_address.get('district')

        partner_vals = {
            'name': billing_address.get('name') or 'Guest Customer',
            'email': email,
            'phone': billing_address.get('phone'),
            'street': billing_address.get('street'),
            'street2': district if district else False,  # District as street2
            'city': billing_address.get('city'),
            'zip': billing_address.get('zip'),
            'country_id': int(country_id) if country_id else False,
            'state_id': int(state_id) if state_id else False,
            'company_name': billing_address.get('company_name'),
            'vat': billing_address.get('vat'),
        }

        return Partner.create(partner_vals)

    def _create_sale_order(self, cart, partner, agency_data, payment_method):
        """Create sale order from cart"""
        try:
            SaleOrder = request.env['sale.order'].sudo()

            # Parse visit date
            visit_date = cart.get('visit_date')

            # Get agency for commission settings
            agency = request.env['travel.agency'].sudo().browse(agency_data.get('id'))
            commission_type = 'gross'
            commission_percentage = 0.0

            # Safely get commission settings
            try:
                if agency.exists() and hasattr(agency, 'commission_type'):
                    commission_type = agency.commission_type or 'gross'
                if agency.exists() and hasattr(agency, 'commission_percentage'):
                    commission_percentage = agency.commission_percentage or 0.0
            except Exception:
                pass

            # Find EUR pricelist to match ticket prices
            eur_currency = request.env['res.currency'].sudo().search([('name', '=', 'EUR')], limit=1)
            eur_pricelist = None
            if eur_currency:
                eur_pricelist = request.env['product.pricelist'].sudo().search([
                    ('currency_id', '=', eur_currency.id),
                    ('active', '=', True)
                ], limit=1)

            order_vals = {
                'partner_id': partner.id,
                'client_order_ref': f"AGENCY_{agency_data['id']}_{int(datetime.now().timestamp())}",
            }

            # Set EUR pricelist if available
            if eur_pricelist:
                order_vals['pricelist_id'] = eur_pricelist.id

            # Add ticket_date if field exists
            if 'ticket_date' in SaleOrder._fields:
                order_vals['ticket_date'] = visit_date

            # Try to create order - first without commission fields for compatibility
            order = SaleOrder.create(order_vals)

            # Try to update commission fields separately (they may not exist in DB yet)
            # Check if columns actually exist in database, not just in model
            try:
                request.env.cr.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'sale_order' AND column_name = 'agency_id'
                """)
                has_commission_columns = bool(request.env.cr.fetchone())

                if has_commission_columns:
                    commission_vals = {}
                    if agency.exists():
                        commission_vals['agency_id'] = agency.id
                    commission_vals['commission_type'] = commission_type
                    commission_vals['commission_percentage'] = commission_percentage
                    if commission_vals:
                        order.write(commission_vals)
            except Exception as e:
                _logger.warning(f"Could not set commission fields: {e}")

            # Create order lines
            order_total = 0.0
            for line in cart.get('lines', []):
                product_id = line.get('variant_id') or line.get('product_id')
                product = request.env['product.product'].sudo().browse(int(product_id))

                if product.exists():
                    # For Net commission type, the price already includes commission
                    # For Gross, price is base price and commission is calculated separately
                    price_unit = line.get('price', product.list_price)

                    request.env['sale.order.line'].sudo().create({
                        'order_id': order.id,
                        'product_id': product.id,
                        'product_uom_qty': line.get('quantity', 1),
                        'price_unit': price_unit,
                    })

                    order_total += price_unit * line.get('quantity', 1)

            # Calculate and save commission amount
            try:
                # Check if commission_amount column exists in DB
                request.env.cr.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'sale_order' AND column_name = 'commission_amount'
                """)
                has_commission_amount = bool(request.env.cr.fetchone())

                if has_commission_amount and commission_percentage > 0:
                    if commission_type == 'gross':
                        # Gross: commission is percentage of base price
                        commission_amount = order_total * (commission_percentage / 100)
                    else:
                        # Net: price shown includes commission, calculate commission from total
                        # If price = base * (1 + commission%), then commission = price - base
                        # base = price / (1 + commission%), commission = price - base
                        base_amount = order_total / (1 + commission_percentage / 100)
                        commission_amount = order_total - base_amount

                    order.write({'commission_amount': commission_amount})
                    _logger.info(f"Order {order.name}: Commission {commission_type} {commission_percentage}% = {commission_amount}")
            except Exception as e:
                _logger.warning(f"Could not set commission_amount: {e}")

            return order

        except Exception as e:
            _logger.error(f"Error creating sale order: {str(e)}", exc_info=True)
            return None

    def _save_order_visitors(self, order, visitors):
        """Save visitor information to order - creates visitor.form records"""
        try:
            if not visitors:
                return

            VisitorForm = request.env['visitor.form'].sudo()

            for v in visitors:
                # Get product template ID
                product_template_id = v.get('product_template_id')
                if not product_template_id:
                    product_id = v.get('product_id') or v.get('variant_id')
                    if product_id:
                        product = request.env['product.product'].sudo().browse(int(product_id))
                        product_template_id = product.product_tmpl_id.id if product.exists() else False

                # Create visitor.form record
                visitor_vals = {
                    'sale_order_id': order.id,
                    'visitor_first_name': v.get('first_name', '') or v.get('visitor_first_name', ''),
                    'visitor_last_name': v.get('last_name', '') or v.get('visitor_last_name', ''),
                    'visitor_phone': v.get('phone', '') or v.get('visitor_phone', ''),
                    'visitor_email': v.get('email', '') or v.get('visitor_email', ''),
                    'visitor_identity': v.get('identity', '') or v.get('visitor_identity', ''),
                    'product_template_id': int(product_template_id) if product_template_id else False,
                    'visitor_index': v.get('visitor_index', 0),
                }

                VisitorForm.create(visitor_vals)
                _logger.info(f"Created visitor record for order {order.name}: {visitor_vals.get('visitor_first_name')} {visitor_vals.get('visitor_last_name')}")

        except Exception as e:
            _logger.error(f"Error saving order visitors: {str(e)}", exc_info=True)

    def _create_payment_transaction(self, order, provider):
        """Create payment transaction for credit card"""
        try:
            Transaction = request.env['payment.transaction'].sudo()

            transaction = Transaction.create({
                'provider_id': provider.id,
                'amount': order.amount_total,
                'currency_id': order.currency_id.id,
                'partner_id': order.partner_id.id,
                'reference': f"TICKET-{order.name}",
                'sale_order_ids': [(4, order.id)],
            })

            return transaction

        except Exception as e:
            _logger.error(f"Error creating payment transaction: {str(e)}")
            return None

    def _update_inventory(self, cart):
        """Update daily inventory for sold tickets"""
        try:
            visit_date = cart.get('visit_date')
            if not visit_date:
                return

            DailyInventory = request.env['eth.daily.inventory'].sudo()

            for line in cart.get('lines', []):
                product_id = line.get('variant_id') or line.get('product_id')
                quantity = line.get('quantity', 0)

                if product_id and quantity > 0:
                    inventory = DailyInventory.search([
                        ('product_id', '=', int(product_id)),
                        ('date', '=', visit_date),
                        ('state', '=', 'confirmed')
                    ], limit=1)

                    if inventory:
                        # Update sale quantity
                        inventory.sale_qty += quantity
                        _logger.info(f"Updated inventory for product {product_id}: +{quantity} sales")

        except Exception as e:
            _logger.error(f"Error updating inventory: {str(e)}")

    # ==================== Confirmation Page ====================

    @http.route('/agency/tickets/checkout/confirmation/<int:order_id>', type='http', auth="public", website=True, csrf=False)
    def confirmation_page(self, order_id, **kw):
        """Order confirmation page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists():
                return request.redirect('/agency/tickets')

            values = self._prepare_values(
                page_name='checkout_confirmation',
                order=order
            )
            return request.render('eth_agency_portal.agency_checkout_confirmation', values)

        except Exception as e:
            _logger.error(f"Error in confirmation page: {str(e)}", exc_info=True)
            return request.redirect('/agency/tickets')
