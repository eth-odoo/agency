# -*- coding: utf-8 -*-
{
    'name': 'Agency Core',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Core agency management - base module for Ticket and Travel',
    'description': """
Agency Core Module
==================
Base module for agency management that works with both Ticket and Travel systems.

Features:
---------
* Agency registration and approval workflow
* Agency user management with authentication
* Permission-based access control
* Password reset functionality
* Membership purposes management
* CRM integration for agency management
* Email notifications

This module has NO hotel dependencies, making it suitable for both
Ticket and Travel deployments.
    """,
    'author': 'ETH',
    'website': 'https://www.eth.com',
    'depends': [
        'base',
        'crm',
        'contacts',
        'portal',
        'website',
        'mail',
        'sale',
        'account',
    ],
    'data': [
        # Security
        'security/agency_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence_data.xml',
        'data/membership_purpose_data.xml',
        'data/email_templates.xml',

        # Views
        'views/agency_views.xml',
        'views/agency_registration_views.xml',
        'views/agency_user_views.xml',
        'views/agency_config_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'eth_agency_core/static/src/css/agency.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
