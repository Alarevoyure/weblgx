# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WeblgxBot',
    'author': 'LOEGAUX - Propriété de Ferme 201 SARL',
    'version': '1.2',
    'category': 'Productivity/Discuss',
    'summary': 'Add WeblgxBot in discussions',
    'website': 'https://www.loegaux.fr/app/discuss',
    'depends': ['mail'],
    'auto_install': True,
    'installable': True,
    'data': [
        'views/res_users_views.xml',
        'data/mailbot_data.xml',
    ],
    'demo': [
        'data/mailbot_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mail_bot/static/src/scss/odoobot_style.scss',
        ],
    },
    'license': 'LGPL-3',
}
