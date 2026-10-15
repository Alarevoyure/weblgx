# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.http import request


class Website(models.Model):
    _inherit = "website"

    @api.model
    def get_current_website(self, fallback=True):
        website = super().get_current_website(fallback=fallback)
        user = self.env.user
        if (
            not website
            or self.env.su
            or not user
            or user._is_public()
            or not user.company_ids
        ):
            return website

        # Ne pas interférer avec le routage frontend (y compris pendant _match).
        if request and (
            getattr(request, "is_frontend", False)
            or not request.httprequest.path.startswith("/web")
        ):
            return website

        website_company = website.sudo().company_id
        if website_company in user.company_ids:
            return website

        company_website = user.company_id.sudo().website_id
        if (
            company_website
            and company_website.company_id in user.company_ids
        ):
            return company_website

        return (
            self.sudo().search(
                [("company_id", "in", user.company_ids.ids)],
                limit=1,
            )
            or website
        )
