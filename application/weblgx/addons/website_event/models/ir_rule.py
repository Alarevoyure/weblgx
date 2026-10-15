# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request
from odoo.osv import expression


class IrRule(models.Model):
    _inherit = "ir.rule"

    def _compute_domain(self, model_name, mode="read"):
        domain = super()._compute_domain(model_name, mode)
        if model_name != "event.event" or self.env.su or self.env.user.has_group("base.group_system"):
            return domain
        website_id = self.env.context.get("website_id")
        if not website_id and request and getattr(request, "is_frontend", False):
            website = self.env["website"].get_current_website(fallback=False)
            if website:
                website_id = website.id
        if website_id:
            domain = expression.AND([domain, [("website_id", "=", website_id)]])
        return domain
