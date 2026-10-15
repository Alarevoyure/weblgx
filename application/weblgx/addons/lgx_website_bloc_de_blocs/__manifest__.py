# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Bloc de blocs",
    "summary": "Colonnes (1–6) dans lesquelles on peut déposer d'autres blocs du site.",
    "version": "17.0.1.0.0",
    "category": "Website/Website",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["website", "lgx_brand_midnight"],
    "data": [
        "views/snippets/s_bloc_de_blocs.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "lgx_website_bloc_de_blocs/static/src/snippets/s_bloc_de_blocs/000.scss",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_bloc_de_blocs/static/src/snippets/s_bloc_de_blocs/options.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
