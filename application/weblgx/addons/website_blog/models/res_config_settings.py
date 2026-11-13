# -*- coding: utf-8 -*-

from weblgx import fields, models
from weblgx.exceptions import UserError
from weblgx.tools.translate import _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    plexipost_receiver_url = fields.Char(
        related="website_id.plexipost_receiver_url",
        groups="website.group_website_designer",
    )
    plexipost_client_id = fields.Char(
        related="website_id.plexipost_client_id",
        readonly=False,
        groups="website.group_website_designer",
    )
    plexipost_client_secret = fields.Char(
        related="website_id.plexipost_client_secret",
        readonly=False,
        groups="website.group_website_designer",
    )
    plexipost_blog_id = fields.Many2one(
        related="website_id.plexipost_blog_id",
        readonly=False,
        domain="[('website_id', '=', website_id)]",
        groups="website.group_website_designer",
    )

    def action_plexipost_generate_credentials(self):
        self.ensure_one()
        if not self.website_id:
            raise UserError(_("Select a website first."))
        self.website_id.action_plexipost_generate_credentials()
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
