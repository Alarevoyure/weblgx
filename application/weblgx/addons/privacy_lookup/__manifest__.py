# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Privacy',
    'author': 'LOEGAUX - Propriété de Ferme 201 SARL',
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['mail'],
    'data': [
        'wizard/privacy_lookup_wizard_views.xml',
        'views/privacy_log_views.xml',
        'security/ir.model.access.csv',
        'data/ir_actions_server_data.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
