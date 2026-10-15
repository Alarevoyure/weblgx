# -*- coding: utf-8 -*-
{
    "name": "LGX — isolation des médias par site",
    "summary": "Isole les images et documents uploadés par site web (SaaS multi-client)",
    "version": "17.0.1.0.3",
    "category": "Website",
    "depends": ["website"],
    "data": [
        "security/attachment_isolation_security.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "lgx_website_attachment_isolation/static/src/components/upload_progress_toast/upload_service.js",
        ],
        "website.assets_wysiwyg": [
            "lgx_website_attachment_isolation/static/src/components/media_dialog/file_selector.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
