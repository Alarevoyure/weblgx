# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ImLivechatChannel(models.Model):
    _inherit = "im_livechat.channel"

    website_id = fields.Many2one(
        "website",
        string="Site web",
        ondelete="restrict",
        index=True,
        help="Site web auquel ce canal est rattaché.",
    )
    company_id = fields.Many2one(
        "res.company",
        related="website_id.company_id",
        store=True,
        index=True,
    )

    @api.model
    def _get_allowed_company_ids(self):
        return self.env.user.company_ids.ids

    @api.model
    def _get_operator_base_domain(self):
        portal_group = self.env.ref("base.group_portal")
        return [
            ("share", "=", False),
            ("groups_id", "not in", portal_group.ids),
        ]

    def _get_operator_domain(self):
        self.ensure_one()
        domain = self._get_operator_base_domain()
        if self.website_id:
            domain.append(("company_ids", "in", self.website_id.company_id.ids))
        else:
            domain.append(("company_ids", "in", self._get_allowed_company_ids()))
        return domain

    @api.model
    def _sync_all_website_links(self):
        websites = self.env["website"].sudo().search([("channel_id", "!=", False)])
        for website in websites:
            website.channel_id.sudo().write({"website_id": website.id})

    @api.constrains("website_id", "user_ids")
    def _check_operators_company(self):
        for channel in self:
            if not channel.website_id:
                continue
            company = channel.website_id.company_id
            invalid_users = channel.user_ids.filtered(
                lambda user: company not in user.company_ids
            )
            if invalid_users:
                raise ValidationError(
                    _(
                        "Les opérateurs suivants n'appartiennent pas à la société du site « %(website)s » : %(users)s",
                        website=channel.website_id.name,
                        users=", ".join(invalid_users.mapped("name")),
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("website_id"):
                website_id = (
                    self.env.context.get("default_website_id")
                    or self.env.context.get("website_id")
                )
                if website_id:
                    vals["website_id"] = website_id
        channels = super().create(vals_list)
        channels._sync_website_channel_link()
        return channels

    def write(self, vals):
        res = super().write(vals)
        if "website_id" in vals:
            self._sync_website_channel_link()
        return res

    def _sync_website_channel_link(self):
        Website = self.env["website"].sudo()
        for channel in self:
            if not channel.website_id:
                continue
            other_channels = self.search([
                ("website_id", "=", channel.website_id.id),
                ("id", "!=", channel.id),
            ])
            if other_channels:
                other_channels.write({"website_id": False})
            if channel.website_id.channel_id != channel:
                channel.website_id.write({"channel_id": channel.id})
