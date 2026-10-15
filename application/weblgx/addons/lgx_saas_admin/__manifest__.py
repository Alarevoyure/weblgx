# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Administration multi-société",
    "summary": (
        "SuperAdmin (vision globale) et Admin société "
        "(limité aux sociétés dont il est membre)."
    ),
    "version": "17.0.1.0.2",
    "category": "Administration",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["base", "base_setup", "calendar"],
    "data": [
        "security/saas_admin_groups.xml",
        "security/saas_admin_security.xml",
        "security/ir.model.access.csv",
        "security/saas_admin_functions.xml",
        "data/saas_record_rules.xml",
        "views/res_users_views.xml",
        "views/res_company_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
