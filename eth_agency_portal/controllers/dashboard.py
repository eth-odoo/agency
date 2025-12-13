# -*- coding: utf-8 -*-
import logging
from odoo import http, _
from odoo.http import request
from .base import AgencyPortalBase, require_auth, auto_language

_logger = logging.getLogger(__name__)


class DashboardController(AgencyPortalBase):
    """Dashboard controller"""

    @http.route('/agency/dashboard', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def agency_dashboard(self, **kwargs):
        """Agency dashboard page"""
        try:
            # Get user data first
            user_data = self._get_current_user()
            if not user_data:
                _logger.warning("Dashboard: No user data found")
                return request.redirect('/agency/login')

            # Get permissions safely
            permissions = user_data.get('permissions', {})
            _logger.info(f"Dashboard permissions: {permissions}")

            # Check permissions (more lenient - if no permission system, allow)
            if permissions and not permissions.get('dashboard_view', True):
                _logger.warning(f"User {user_data.get('name')} doesn't have dashboard_view permission")
                values = self._prepare_values(
                    page_name='access_denied',
                    message=_('You do not have permission to view the dashboard.')
                )
                return request.render('eth_agency_portal.agency_access_denied', values)

            # Get agency data
            agency_data = self._get_agency_data()

            # Get statistics (example - replace with real logic)
            stats = {
                'total_bookings': 150,
                'pending_bookings': 12,
                'total_sales': 50000,
                'month_sales': 15000,
            }

            # Prepare values once
            values = self._prepare_values(
                page_name='dashboard',
                stats=stats,
            )

            return request.render('eth_agency_portal.agency_dashboard', values)

        except Exception as e:
            _logger.error(f"Error in dashboard: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            # Redirect to login on any error
            return request.redirect('/agency/login')
