# -*- coding: utf-8 -*-
{
    "name": "LDAP Web@LGX - Rechargement utilisateurs",
    "summary": (
        "Bouton dans Utilisateurs pour importer, mettre à jour et "
        "désactiver les comptes absents de l'annuaire LDAP."
    ),
    "version": "17.0.1.1.0",
    "category": "Customizations",
    "depends": ["auth_ldap", "lgx_auth_ldap"],
    "data": [
        "views/res_users_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
