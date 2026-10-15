# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Link Tracker',
    'author': 'LOEGAUX - Propriété de Ferme 201 SARL',
    'category': 'Marketing',
    'description': """
Shorten URLs and use them to track clicks and UTMs
""",
    'version': '1.1',
    'depends': ['utm', 'mail'],
    'data': [
        'views/link_tracker_views.xml',
        'views/utm_campaign_views.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}
