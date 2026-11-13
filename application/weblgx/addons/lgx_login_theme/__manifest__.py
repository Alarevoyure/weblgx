# -*- coding: utf-8 -*-
{
    "name": "LGX Login — boutons bleu nuit",
    "summary": "Connexion (boutons primaires) et sélecteur de langue en bleu nuit",
    "version": "17.0.1.2.0",
    "category": "Customizations",
    "depends": ["web", "auth_signup"],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
    "assets": {
        "web.assets_frontend": [
            "lgx_login_theme/static/src/css/login_btn_midnight.css",
            "lgx_login_theme/static/src/css/lang_selector_midnight.css",
        ],
    },
}
