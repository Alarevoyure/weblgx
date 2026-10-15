# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Bloc Partenaires",
    "summary": "Bloc éditeur web : carrousel de logos partenaires (1 à 20, 6 visibles).",
    "description": "Carrousel de logos partenaires sur la page du site.",
    "version": "17.0.1.1.0",
    "category": "Website/Website",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["website", "lgx_brand_midnight"],
    "data": [
        "views/snippets/s_partenaires.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "lgx_website_partenaires/static/src/snippets/s_partenaires/000.js",
            "lgx_website_partenaires/static/src/snippets/s_partenaires/000.scss",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_partenaires/static/src/snippets/s_partenaires/options.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
