# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Bloc Colonnes Editables",
    "summary": "Bloc éditeur web : colonnes avec taille d'image, dimensions et zone texte/média.",
    "version": "17.0.1.0.0",
    "category": "Website/Website",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["website", "lgx_brand_midnight"],
    "data": [
        "views/snippets/s_colonnes_editables.xml",
        "views/snippets/snippets.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "lgx_website_colonnes_editables/static/src/snippets/s_colonnes_editables/000.scss",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_colonnes_editables/static/src/snippets/s_colonnes_editables/options.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
