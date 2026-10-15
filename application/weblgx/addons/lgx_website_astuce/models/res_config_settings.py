# -*- coding: utf-8 -*-
from weblgx import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    deepseek_api_key = fields.Char(
        related="website_id.deepseek_api_key",
        readonly=False,
    )
