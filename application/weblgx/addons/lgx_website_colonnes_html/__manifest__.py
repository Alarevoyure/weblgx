# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Colonnes HTML",
    "summary": "Bloc éditeur web : 1 à 6 colonnes de code HTML côte à côte, éditables via Ace.",
    "description": "Bloc de 1 a 6 colonnes de code HTML, editables dans l'editeur du site.",
    "version": "17.0.1.1.0",
    "category": "Website/Website",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["website", "lgx_brand_midnight"],
    "data": [
        "views/snippets/s_colonnes_html.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "lgx_website_colonnes_html/static/src/snippets/s_colonnes_html/000.js",
            "lgx_website_colonnes_html/static/src/snippets/s_colonnes_html/000.scss",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_colonnes_html/static/src/snippets/s_colonnes_html/options.js",
            "lgx_website_colonnes_html/static/src/snippets/s_colonnes_html/save_patch.js",
            "lgx_website_colonnes_html/static/src/xml/s_colonnes_html_dialog.xml",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
