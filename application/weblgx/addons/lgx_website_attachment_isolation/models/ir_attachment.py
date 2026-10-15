# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.osv import expression


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        domain = list(domain)
        website_id = self.env.context.get("website_id")
        if website_id and not self.env.su and not self.env.user.has_group("lgx_saas_admin.group_superadmin"):
            domain = expression.AND([
                domain,
                ["|", ("website_id", "=", False), ("website_id", "=", website_id)],
            ])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )

    @api.model_create_multi
    def create(self, vals_list):
        website_id = self.env.context.get("website_id")
        if website_id:
            website = self.env["website"].browse(website_id).exists()
        else:
            website = self.env["website"].get_current_website(fallback=False)
        if website:
            for vals in vals_list:
                if (
                    vals.get("res_model") == "ir.ui.view"
                    and not vals.get("res_id")
                    and "website_id" not in vals
                    and "not_force_website_id" not in self.env.context
                ):
                    vals["website_id"] = website.id
        return super().create(vals_list)
