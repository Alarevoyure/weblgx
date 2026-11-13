# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

from weblgx import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    channel_id = fields.Many2one('im_livechat.channel', string='Website Live Channel', related='website_id.channel_id', readonly=False)
