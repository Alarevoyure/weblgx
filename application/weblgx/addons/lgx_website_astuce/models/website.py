# -*- coding: utf-8 -*-
from weblgx import fields, models


class Website(models.Model):
    _inherit = "website"

    deepseek_api_key = fields.Char(
        string="Clé API DeepSeek",
        groups="base.group_system,website.group_website_designer",
        help="Clé API DeepSeek (platform.deepseek.com), isolée par site web.",
    )
    astuce_ids = fields.One2many(
        "website.astuce",
        "website_id",
        string="Astuces du jour",
    )
