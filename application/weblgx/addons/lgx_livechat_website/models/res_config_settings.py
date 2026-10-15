# -*- coding: utf-8 -*-

from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    @api.onchange("website_id")
    def _onchange_website_id_livechat_channel(self):
        if self.channel_id and self.channel_id.website_id not in (False, self.website_id):
            self.channel_id = False
