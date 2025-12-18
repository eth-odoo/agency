# -*- coding: utf-8 -*-
"""
Ticket Overview Controller for Agency Portal
Handles listing, viewing, editing, and deleting ticket orders
"""
import logging
from datetime import datetime, timedelta
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase

_logger = logging.getLogger(__name__)


class TicketOverviewController(AgencyPortalBase):
    """Ticket Overview controllers"""

    # ==================== Overview Page ====================

    @http.route('/agency/tickets/overview', type='http', auth="public", website=True, csrf=False)
    def ticket_overview_page(self, **kw):
        """Ticket overview page - dashboard + list"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            if not agency_data:
                return request.redirect('/agency/login')

            # Get filter parameters
            date_from = kw.get('date_from')
            date_to = kw.get('date_to')
            status = kw.get('status', 'all')
            search = kw.get('search', '')

            # Build domain for orders
            domain = self._build_order_domain(agency_data, date_from, date_to, status, search)

            # Get orders
            orders = request.env['sale.order'].sudo().search(
                domain,
                order='date_order desc',
                limit=100
            )

            # Calculate statistics
            stats = self._calculate_stats(agency_data)

            values = self._prepare_values(
                page_name='ticket_overview',
                orders=orders,
                stats=stats,
                filters={
                    'date_from': date_from,
                    'date_to': date_to,
                    'status': status,
                    'search': search
                }
            )
            return request.render('eth_agency_portal.agency_ticket_overview', values)

        except Exception as e:
            _logger.error(f"Error in ticket overview page: {str(e)}", exc_info=True)
            return request.redirect('/agency/dashboard')

    def _build_order_domain(self, agency_data, date_from, date_to, status, search):
        """Build search domain for orders"""
        domain = [
            ('client_order_ref', 'like', f"AGENCY_{agency_data['id']}_")
        ]

        if date_from:
            domain.append(('date_order', '>=', date_from))
        if date_to:
            domain.append(('date_order', '<=', date_to))

        if status and status != 'all':
            domain.append(('state', '=', status))

        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            domain.append(('partner_id.name', 'ilike', search))

        return domain

    def _calculate_stats(self, agency_data):
        """Calculate dashboard statistics"""
        SaleOrder = request.env['sale.order'].sudo()
        base_domain = [('client_order_ref', 'like', f"AGENCY_{agency_data['id']}_")]

        # Total orders
        total_orders = SaleOrder.search_count(base_domain)

        # Today's orders
        today = datetime.now().date()
        today_domain = base_domain + [('date_order', '>=', str(today))]
        today_orders = SaleOrder.search_count(today_domain)

        # This month's orders
        month_start = today.replace(day=1)
        month_domain = base_domain + [('date_order', '>=', str(month_start))]
        month_orders = SaleOrder.search_count(month_domain)

        # Total revenue and commission
        orders = SaleOrder.search(base_domain)
        total_revenue = sum(orders.mapped('amount_total'))

        # Check if commission_amount column exists
        total_commission = 0
        try:
            request.env.cr.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'sale_order' AND column_name = 'commission_amount'
            """)
            if request.env.cr.fetchone():
                total_commission = sum(orders.mapped('commission_amount') or [0])
        except Exception:
            pass

        # Pending orders (draft)
        pending_domain = base_domain + [('state', '=', 'draft')]
        pending_orders = SaleOrder.search_count(pending_domain)

        # Confirmed orders (sale)
        confirmed_domain = base_domain + [('state', '=', 'sale')]
        confirmed_orders = SaleOrder.search_count(confirmed_domain)

        return {
            'total_orders': total_orders,
            'today_orders': today_orders,
            'month_orders': month_orders,
            'total_revenue': total_revenue,
            'total_commission': total_commission,
            'pending_orders': pending_orders,
            'confirmed_orders': confirmed_orders,
        }

    # ==================== View Order ====================

    @http.route('/agency/tickets/overview/<int:order_id>', type='http', auth="public", website=True, csrf=False)
    def view_order(self, order_id, **kw):
        """View order details"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            if not agency_data:
                return request.redirect('/agency/login')

            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists() or f"AGENCY_{agency_data['id']}_" not in (order.client_order_ref or ''):
                return request.redirect('/agency/tickets/overview')

            # Get visitors
            visitors = order.visitor_form_ids if hasattr(order, 'visitor_form_ids') else []

            values = self._prepare_values(
                page_name='ticket_order_detail',
                order=order,
                visitors=visitors
            )
            return request.render('eth_agency_portal.agency_ticket_order_detail', values)

        except Exception as e:
            _logger.error(f"Error viewing order: {str(e)}", exc_info=True)
            return request.redirect('/agency/tickets/overview')

    # ==================== Edit Order ====================

    @http.route('/agency/tickets/overview/<int:order_id>/edit', type='http', auth="public", website=True, csrf=False)
    def edit_order_page(self, order_id, **kw):
        """Edit order page"""
        try:
            if not self._is_authenticated():
                return request.redirect('/agency/login')

            agency_data = self._get_agency_data()
            if not agency_data:
                return request.redirect('/agency/login')

            order = request.env['sale.order'].sudo().browse(order_id)
            if not order.exists() or f"AGENCY_{agency_data['id']}_" not in (order.client_order_ref or ''):
                return request.redirect('/agency/tickets/overview')

            # Can only edit draft orders
            if order.state != 'draft':
                return request.redirect(f'/agency/tickets/overview/{order_id}')

            # Get visitors
            visitors = order.visitor_form_ids if hasattr(order, 'visitor_form_ids') else []

            values = self._prepare_values(
                page_name='ticket_order_edit',
                order=order,
                visitors=visitors
            )
            return request.render('eth_agency_portal.agency_ticket_order_edit', values)

        except Exception as e:
            _logger.error(f"Error editing order: {str(e)}", exc_info=True)
            return request.redirect('/agency/tickets/overview')

    @http.route('/agency/api/tickets/order/update', type='json', auth='public', methods=['POST'], csrf=False)
    def update_order(self, order_id, visitors=None, **kw):
        """Update order visitors"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            order = request.env['sale.order'].sudo().browse(int(order_id))
            if not order.exists() or f"AGENCY_{agency_data['id']}_" not in (order.client_order_ref or ''):
                return {'success': False, 'error': 'Order not found'}

            if order.state != 'draft':
                return {'success': False, 'error': 'Cannot edit confirmed orders'}

            # Update visitors
            if visitors:
                self._update_order_visitors(order, visitors)

            return {'success': True, 'message': 'Order updated successfully'}

        except Exception as e:
            _logger.error(f"Error updating order: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _update_order_visitors(self, order, visitors):
        """Update visitor records for order"""
        VisitorForm = request.env['visitor.form'].sudo()

        # Delete existing visitors
        if hasattr(order, 'visitor_form_ids'):
            order.visitor_form_ids.unlink()

        # Create new visitors
        for v in visitors:
            product_template_id = v.get('product_template_id')
            if not product_template_id:
                product_id = v.get('product_id')
                if product_id:
                    product = request.env['product.product'].sudo().browse(int(product_id))
                    product_template_id = product.product_tmpl_id.id if product.exists() else False

            VisitorForm.create({
                'sale_order_id': order.id,
                'visitor_first_name': v.get('first_name', ''),
                'visitor_last_name': v.get('last_name', ''),
                'visitor_phone': v.get('phone', ''),
                'visitor_email': v.get('email', ''),
                'visitor_identity': v.get('identity', ''),
                'product_template_id': int(product_template_id) if product_template_id else False,
                'visitor_index': v.get('visitor_index', 0),
            })

    # ==================== Delete Order ====================

    @http.route('/agency/api/tickets/order/delete', type='json', auth='public', methods=['POST'], csrf=False)
    def delete_order(self, order_id, **kw):
        """Delete/Cancel order"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            order = request.env['sale.order'].sudo().browse(int(order_id))
            if not order.exists() or f"AGENCY_{agency_data['id']}_" not in (order.client_order_ref or ''):
                return {'success': False, 'error': 'Order not found'}

            # Cancel order
            if order.state == 'draft':
                # Delete draft orders
                order.unlink()
                return {'success': True, 'message': 'Order deleted successfully'}
            else:
                # Cancel confirmed orders
                order.action_cancel()
                return {'success': True, 'message': 'Order cancelled successfully'}

        except Exception as e:
            _logger.error(f"Error deleting order: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    # ==================== API Endpoints ====================

    @http.route('/agency/api/tickets/orders', type='json', auth='public', methods=['POST'], csrf=False)
    def get_orders(self, page=1, limit=20, **kw):
        """Get orders list (paginated)"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            agency_data = self._get_agency_data()
            if not agency_data:
                return {'success': False, 'error': 'Agency not found'}

            domain = [('client_order_ref', 'like', f"AGENCY_{agency_data['id']}_")]

            # Apply filters
            if kw.get('date_from'):
                domain.append(('date_order', '>=', kw['date_from']))
            if kw.get('date_to'):
                domain.append(('date_order', '<=', kw['date_to']))
            if kw.get('status') and kw['status'] != 'all':
                domain.append(('state', '=', kw['status']))
            if kw.get('search'):
                domain.extend(['|', ('name', 'ilike', kw['search']), ('partner_id.name', 'ilike', kw['search'])])

            # Count total
            total = request.env['sale.order'].sudo().search_count(domain)

            # Get paginated orders
            offset = (int(page) - 1) * int(limit)
            orders = request.env['sale.order'].sudo().search(
                domain,
                order='date_order desc',
                limit=int(limit),
                offset=offset
            )

            order_list = []
            for order in orders:
                order_list.append({
                    'id': order.id,
                    'name': order.name,
                    'date_order': order.date_order.strftime('%Y-%m-%d %H:%M') if order.date_order else '',
                    'ticket_date': order.ticket_date.strftime('%Y-%m-%d') if hasattr(order, 'ticket_date') and order.ticket_date else '',
                    'partner_name': order.partner_id.name if order.partner_id else '',
                    'amount_total': order.amount_total,
                    'state': order.state,
                    'visitor_count': len(order.visitor_form_ids) if hasattr(order, 'visitor_form_ids') else 0,
                })

            return {
                'success': True,
                'orders': order_list,
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + int(limit) - 1) // int(limit)
            }

        except Exception as e:
            _logger.error(f"Error getting orders: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
