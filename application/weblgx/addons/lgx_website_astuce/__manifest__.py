# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Astuce du jour",
    "summary": "Bloc éditeur web : astuce générée via DeepSeek, renouvelée périodiquement.",
    "version": "17.0.1.1.0",
    "category": "Website/Website",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["website", "lgx_brand_midnight"],
    "data": [
        "security/astuce_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/website_astuce_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
        "views/snippets/s_astuce.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "lgx_website_astuce/static/src/css/astuce_backend.css",
        ],
        "web.assets_frontend": [
            "lgx_website_astuce/static/src/snippets/s_astuce/000.js",
            "lgx_website_astuce/static/src/snippets/s_astuce/000.scss",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_astuce/static/src/snippets/s_astuce/options.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
