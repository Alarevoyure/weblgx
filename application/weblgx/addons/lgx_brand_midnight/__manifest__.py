# -*- coding: utf-8 -*-
{
    "name": "LGX — marque bleu nuit (global)",
    "summary": "Couleur primaire Odoo (backend, boutons, menus) + Bootstrap frontend en bleu nuit #16213e",
    "version": "17.0.1.0.0",
    "category": "Customizations",
    "depends": ["web"],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
    "assets": {
        "web._assets_primary_variables": [
            (
                "before",
                "web/static/src/scss/primary_variables.scss",
                "lgx_brand_midnight/static/src/scss/brand_pre_variables.scss",
            ),
        ],
        "web._assets_frontend_helpers": [
            (
                "after",
                "web/static/src/scss/bootstrap_overridden_frontend.scss",
                "lgx_brand_midnight/static/src/scss/frontend_primary.scss",
            ),
        ],
        "web.assets_frontend": [
            (
                "after",
                "web/static/src/legacy/scss/lazyloader.scss",
                "lgx_brand_midnight/static/src/css/brand_frontend_tail.css",
            ),
        ],
    },
}
