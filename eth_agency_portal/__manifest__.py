# -*- coding: utf-8 -*-
{
    'name': 'Agency Portal',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Agency self-service portal',
    'description': """
Agency Portal
=============
Self-service portal for agency users.

Features:
---------
* Agency login and authentication
* Dashboard
* User management
* Profile management
* Bonus reservations
* Bonus wallet view

Architecture:
-------------
This module provides a complete portal interface for agency users.
    """,
    'author': 'ETH',
    'website': 'https://www.eth.com',
    'depends': [
        'website',
        'eth_agency_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/portal_config_data.xml',
        # New templates (eth_travel_agency_web style)
        'templates/auth_templates.xml',
        'templates/base_templates.xml',
        'templates/dashboard_templates.xml',
        'templates/user_management_templates.xml',
        'templates/settings_templates.xml',
        'templates/bonus_wallet_templates.xml',
        'templates/bonus_reservation_template.xml',
        'templates/hotel_bookings_templates.xml',
        'templates/ticket_sales_templates.xml',
        # Other views
        'views/portal_templates.xml',
        'views/portal_profile.xml',
        'views/portal_registration.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'eth_agency_portal/static/src/css/portal.css',
            'eth_agency_portal/static/src/css/registration.css',
            'eth_agency_portal/static/src/js/portal.js',
            'eth_agency_portal/static/src/js/bonus_wallet.js',
            'eth_agency_portal/static/src/js/bonus_reservation.js',
            'eth_agency_portal/static/src/js/hotel_bookings.js',
            'eth_agency_portal/static/src/js/ticket_sales.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
