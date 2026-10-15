# -*- coding: utf-8 -*-
{
    "name": "LGX — Live Chat par site",
    "summary": "Restreint les canaux Live Chat et les opérateurs à la société du site web",
    "version": "17.0.1.0.0",
    "category": "Website/Live Chat",
    "depends": ["website_livechat"],
    "data": [
        "security/livechat_website_security.xml",
        "views/im_livechat_channel_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
