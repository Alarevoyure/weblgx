# -*- coding: utf-8 -*-
from lxml import etree

from odoo import api, models, _
from odoo.exceptions import AccessError


class ResCompany(models.Model):
    _inherit = "res.company"

    def _lgx_is_superadmin(self):
        if self.env.su:
            return True
        return self.env.user.has_group("lgx_saas_admin.group_superadmin")

    @api.model_create_multi
    def create(self, vals_list):
        if not self._lgx_is_superadmin():
            raise AccessError(_(
                "Seul un SuperAdmin peut créer une société."
            ))
        return super().create(vals_list)

    def unlink(self):
        if not self._lgx_is_superadmin():
            raise AccessError(_(
                "Seul un SuperAdmin peut supprimer une société."
            ))
        return super().unlink()

    @api.model
    def lgx_apply_saas_record_rules(self):
        """Apply SaaS record rules (needed when target XML IDs are noupdate)."""
        from odoo.addons.lgx_saas_admin.hooks import apply_saas_record_rules

        apply_saas_record_rules(self.env)

    @api.model
    def get_views(self, views, options=None):
        """Hide Create / Delete for company Admins (non-SuperAdmin)."""
        result = super().get_views(views, options=options)
        if self._lgx_is_superadmin():
            return result
        for view_type, view_data in (result.get("views") or {}).items():
            if not view_data or not view_data.get("arch"):
                continue
            if view_type not in ("list", "tree", "kanban", "form"):
                continue
            arch = etree.fromstring(view_data["arch"])
            arch.set("create", "false")
            arch.set("delete", "false")
            view_data["arch"] = etree.tostring(arch, encoding="unicode")
        return result
