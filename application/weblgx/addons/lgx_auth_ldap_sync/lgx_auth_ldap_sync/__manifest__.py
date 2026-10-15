# -*- coding: utf-8 -*-
{
    "name": "LDAP Web@LGX - Rechargement utilisateurs",
    "summary": (
        "Bouton dans Utilisateurs pour importer et mettre à jour "
        "les comptes depuis l'annuaire LDAP."
    ),
    "version": "17.0.1.0.0",
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
