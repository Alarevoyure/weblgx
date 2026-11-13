# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class MailMessage(models.Model):
    _inherit = "mail.message"

    blog_comment_state = fields.Selection(
        [
            ("pending", "Pending validation"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Blog comment status",
        copy=False,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            for vals in vals_list:
                if vals.get("model") == "blog.post" and vals.get("blog_comment_state") == "approved":
                    post = self.env["blog.post"].browse(vals.get("res_id")).exists()
                    if not post or not post._user_can_moderate_comments():
                        vals["blog_comment_state"] = "pending"
        return super().create(vals_list)

    def write(self, vals):
        if "blog_comment_state" in vals and not self.env.su:
            for message in self.filtered(lambda item: item.model == "blog.post"):
                post = self.env["blog.post"].browse(message.res_id).exists()
                if not post or not post._user_can_moderate_comments():
                    raise AccessError(_("Only a blog administrator can validate a comment."))
        return super().write(vals)
