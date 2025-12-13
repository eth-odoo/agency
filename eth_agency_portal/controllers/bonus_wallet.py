# -*- coding: utf-8 -*-
import logging
from odoo import http, fields, _
from odoo.http import request
from .base import AgencyPortalBase, require_auth, auto_language
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class BonusWalletController(AgencyPortalBase):
    """Bonus wallet management controllers - uses Travel API"""

    @http.route('/agency/bonus-wallet', type='http', auth="public", website=True, csrf=False)
    @require_auth()
    @auto_language
    def bonus_wallet(self, **kw):
        """Main bonus wallet page"""
        try:
            agency_data = self._get_agency_data()
            user_data = self._get_current_user()

            # Check if agency has Bonus purpose
            if not agency_data or not agency_data.get('has_bonus', False):
                return request.render('eth_agency_portal.agency_access_denied',
                    self._prepare_values(
                        page_name='bonus-wallet',
                        message=_('Your agency does not have Bonus membership. Please contact administrator.')
                    ))

            is_master = user_data.get('is_master', False)

            # Prepare values
            values = self._prepare_values(
                page_name='bonus-wallet',
                is_master=is_master,
            )

            return request.render('eth_agency_portal.agency_bonus_wallet', values)

        except Exception as e:
            _logger.error(f"Error in bonus wallet: {str(e)}")
            return request.redirect('/agency/dashboard')

    @http.route('/agency/api/bonus-wallet/info', type='json', auth='public', methods=['POST'], csrf=False)
    def get_wallet_info(self, **kw):
        """Get wallet information via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            if not token:
                return {'success': False, 'error': 'No token'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_bonus_wallet(token)

            if result.get('success'):
                return {
                    'success': True,
                    'data': {
                        'wallets': [{
                            'type': 'agency',
                            'wallet': result.get('data', {}),
                            'owner_info': {
                                'type': 'agency',
                                'name': 'Agency Wallet'
                            }
                        }]
                    }
                }
            else:
                return {'success': False, 'error': result.get('error', 'Failed to get wallet')}

        except Exception as e:
            _logger.error(f"Error in get_wallet_info: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/bonus-wallet/entries', type='json', auth='public', methods=['POST'], csrf=False)
    def get_wallet_entries(self, wallet_type=None, filters=None, **kw):
        """Get bonus entry history via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            if not token:
                return {'success': False, 'error': 'No token'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_bonus_wallet(token)

            if result.get('success'):
                wallet_data = result.get('data', {})
                entries = wallet_data.get('entries', [])
                return {
                    'success': True,
                    'data': {
                        'entries': entries
                    }
                }
            else:
                return {'success': True, 'data': {'entries': []}}

        except Exception as e:
            _logger.error(f"Error in get_wallet_entries: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/bonus-wallet/spends', type='json', auth='public', methods=['POST'], csrf=False)
    def get_wallet_spends(self, wallet_type=None, filters=None, **kw):
        """Get bonus spend history - placeholder"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            # TODO: Implement via Travel API when endpoint is available
            return {'success': True, 'data': {'spends': []}}

        except Exception as e:
            _logger.error(f"Error in get_wallet_spends: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/agency/api/bonus-wallet/summary', type='json', auth='public', methods=['POST'], csrf=False)
    def get_wallet_summary(self, wallet_type=None, period='month', **kw):
        """Get wallet summary for dashboard via Travel API"""
        try:
            if not self._is_authenticated():
                return {'success': False, 'error': 'Unauthorized'}

            token = self._get_token()
            if not token:
                return {'success': False, 'error': 'No token'}

            api_client = request.env['travel.api.client'].sudo()
            result = api_client.get_bonus_wallet(token)

            if result.get('success'):
                wallet_data = result.get('data', {})
                return {
                    'success': True,
                    'data': {
                        'balance': wallet_data.get('balance', 0),
                        'currency': wallet_data.get('currency', 'EUR'),
                        'period_earned': 0,  # TODO: Calculate from entries
                        'period_spent': 0,
                        'expiring_soon': 0,
                        'expiring_entries_count': 0
                    }
                }
            else:
                return {
                    'success': True,
                    'data': {
                        'balance': 0,
                        'currency': 'EUR',
                        'period_earned': 0,
                        'period_spent': 0,
                        'expiring_soon': 0,
                        'expiring_entries_count': 0
                    }
                }

        except Exception as e:
            _logger.error(f"Error in get_wallet_summary: {str(e)}")
            return {'success': False, 'error': str(e)}
