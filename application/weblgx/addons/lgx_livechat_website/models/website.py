# -*- coding: utf-8 -*-

from odoo import models


class Website(models.Model):
    _inherit = "website"

    def write(self, vals):
        previous_channels = {website.id: website.channel_id for website in self}
        res = super().write(vals)
        if "channel_id" in vals:
            for website in self:
                previous_channel = previous_channels[website.id]
                if previous_channel and previous_channel != website.channel_id:
                    previous_channel.sudo().write({"website_id": False})
                if website.channel_id:
                    website.channel_id.sudo().write({"website_id": website.id})
        return res
