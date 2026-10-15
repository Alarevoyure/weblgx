# -*- coding: utf-8 -*-
{
    "name": "Web@LGX - Upload vidéo",
    "summary": "Téléverser des fichiers vidéo (mp4, webm…) dans le sélecteur de médias, comme les images.",
    "description": "Televerser des fichiers video dans le selecteur de medias du site.",
    "version": "17.0.1.0.0",
    "category": "Website/Website",
    "author": "LOEGAUX - Propriété de Ferme 201 SARL",
    "depends": ["website", "lgx_brand_midnight", "lgx_website_attachment_isolation"],
    "assets": {
        "web.assets_frontend": [
            "lgx_website_video_upload/static/src/scss/media_video_upload.scss",
            "lgx_website_video_upload/static/src/js/generate_video_iframe_patch.js",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_video_upload/static/src/scss/media_video_upload.scss",
            "lgx_website_video_upload/static/src/components/media_dialog/video_file_selector.js",
            "lgx_website_video_upload/static/src/components/media_dialog/video_file_selector.xml",
            "lgx_website_video_upload/static/src/components/media_dialog/media_dialog_patch.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
