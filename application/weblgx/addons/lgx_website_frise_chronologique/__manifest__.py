# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Frise chronologique",
    "summary": "Bloc éditeur : frise verticale icône | ligne | date + texte, style maquette.",
    "description": "Frise chronologique verticale : icone, ligne et texte, sur la page du site.",
    "version": "17.0.1.0.0",
    "category": "Website/Website",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["website", "lgx_brand_midnight"],
    "data": [
        "views/snippets/s_frise_chronologique.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "lgx_website_frise_chronologique/static/src/snippets/s_frise_chronologique/000.scss",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_frise_chronologique/static/src/snippets/s_frise_chronologique/options.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
