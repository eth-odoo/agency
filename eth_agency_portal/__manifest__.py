# -*- coding: utf-8 -*-
{
    'name': 'Agency Portal',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Agency self-service portal with API-based data access',
    'description': """
Agency Portal
=============
Self-service portal for agency users.

Features:
---------
* Agency login and authentication
* Profile management
* Bonus reservations (via Travel API)
* Bonus wallet view (via Travel API)
* Hotel information (via Travel API)

Architecture:
-------------
This module uses HTTP APIs to communicate with the Travel system
instead of direct ORM access, allowing it to work across databases.
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
        'views/portal_templates.xml',
        'views/portal_login.xml',
        'views/portal_dashboard.xml',
        'views/portal_bonus.xml',
        'views/portal_profile.xml',
        'views/portal_registration.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'eth_agency_portal/static/src/css/portal.css',
            'eth_agency_portal/static/src/js/portal.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
