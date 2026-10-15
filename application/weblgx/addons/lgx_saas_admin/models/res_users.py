# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import AccessError
from odoo import SUPERUSER_ID


class ResUsers(models.Model):
    _inherit = "res.users"

    def _lgx_is_superadmin(self, user=None):
        """True if user is SuperAdmin or technical superuser."""
        user = user or self.env.user
        if self.env.su or user.id == SUPERUSER_ID:
            return True
        return user.has_group("lgx_saas_admin.group_superadmin")

    def _lgx_privileged_group_xmlids(self):
        # Admin (Settings) may grant Admin. Only SuperAdmin is reserved.
        return (
            "lgx_saas_admin.group_superadmin",
        )

    def _lgx_get_privileged_groups(self):
        groups = self.env["res.groups"]
        for xmlid in self._lgx_privileged_group_xmlids():
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    def _lgx_allowed_company_ids(self):
        return self.env.user.company_ids.ids

    @api.model
    def _lgx_sync_superadmin_companies(self):
        """SuperAdmin is a member of every company, so the switcher and rules match."""
        if self.env.context.get("lgx_skip_superadmin_company_sync"):
            return
        group = self.env.ref("lgx_saas_admin.group_superadmin", raise_if_not_found=False)
        if not group:
            return
        companies = self.env["res.company"].sudo().search([])
        supers = group.with_context(active_test=False).users
        for user in supers:
            missing = companies - user.company_ids
            if not missing:
                continue
            user.with_context(lgx_skip_superadmin_company_sync=True).sudo().write({
                "company_ids": [(4, cid) for cid in missing.ids],
            })

    @api.model
    def _lgx_company_domain(self):
        if self._lgx_is_superadmin():
            return []
        return [("id", "in", self._lgx_allowed_company_ids())]

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        if self._lgx_is_superadmin():
            return res
        domain = self._lgx_company_domain()
        for fname in ("company_ids", "company_id"):
            if fname in res:
                existing = list(res[fname].get("domain") or [])
                res[fname]["domain"] = existing + domain
        return res

    def _lgx_extract_company_ids_from_vals(self, vals, existing=None):
        """Resolve company ids after applying vals to optional existing recordset."""
        existing = existing if existing is not None else self.browse()
        if "company_ids" in vals:
            ids = set(existing.company_ids.ids) if existing else set()
            for command in vals["company_ids"] or []:
                if not command:
                    continue
                op = command[0]
                if op == 6:
                    ids = set(command[2] or [])
                elif op == 5:
                    ids = set()
                elif op == 4:
                    ids.add(command[1])
                elif op in (3, 2):
                    ids.discard(command[1])
            return ids
        if existing:
            return set(existing.company_ids.ids)
        if "company_id" in vals and vals["company_id"]:
            return {vals["company_id"]}
        return set(self.env.company.ids)

    def _lgx_check_companies_allowed(self, company_ids):
        if self._lgx_is_superadmin():
            return
        allowed = set(self._lgx_allowed_company_ids())
        forbidden = set(company_ids) - allowed
        if forbidden:
            raise AccessError(_(
                "Vous ne pouvez rattacher un utilisateur qu'à vos sociétés. "
                "Sociétés non autorisées : %s"
            ) % ", ".join(str(i) for i in sorted(forbidden)))

    def _lgx_extract_group_ids_from_vals(self, vals, existing=None):
        existing = existing if existing is not None else self.browse()
        if "groups_id" not in vals:
            return set(existing.groups_id.ids) if existing else set()
        ids = set(existing.groups_id.ids) if existing else set()
        for command in vals["groups_id"] or []:
            if not command:
                continue
            op = command[0]
            if op == 6:
                ids = set(command[2] or [])
            elif op == 5:
                ids = set()
            elif op == 4:
                ids.add(command[1])
            elif op in (3, 2):
                ids.discard(command[1])
        return ids

    def _lgx_check_no_privilege_escalation(self, new_group_ids, existing=None):
        if self._lgx_is_superadmin():
            return
        privileged = self._lgx_get_privileged_groups()
        if not privileged:
            return
        existing = existing if existing is not None else self.browse()
        previous = set(existing.groups_id.ids) if existing else set()
        added = set(new_group_ids) - previous
        if added & set(privileged.ids):
            raise AccessError(_(
                "Vous n'êtes pas autorisé à attribuer les droits SuperAdmin."
            ))

    def _lgx_check_cannot_edit_superadmin(self):
        if self._lgx_is_superadmin():
            return
        for user in self:
            if user.has_group("lgx_saas_admin.group_superadmin"):
                raise AccessError(_(
                    "Vous n'êtes pas autorisé à modifier un compte SuperAdmin."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        if not self._lgx_is_superadmin():
            allowed = self._lgx_allowed_company_ids()
            for vals in vals_list:
                company_ids = self._lgx_extract_company_ids_from_vals(vals)
                if "company_id" in vals and vals["company_id"]:
                    company_ids.add(vals["company_id"])
                self._lgx_check_companies_allowed(company_ids)
                group_ids = self._lgx_extract_group_ids_from_vals(vals)
                self._lgx_check_no_privilege_escalation(group_ids)
                if "company_ids" not in vals:
                    default_ids = [
                        cid for cid in company_ids if cid in allowed
                    ] or list(allowed[:1])
                    vals["company_ids"] = [(6, 0, default_ids)]
                if "company_id" not in vals:
                    vals["company_id"] = (
                        self.env.company.id
                        if self.env.company.id in allowed
                        else (allowed[0] if allowed else False)
                    )
        users = super().create(vals_list)
        # Propagate company_id to the linked partner for SaaS isolation.
        for user in users:
            if user.company_id and user.partner_id.company_id != user.company_id:
                user.partner_id.sudo().write({"company_id": user.company_id.id})
        return users

    def write(self, vals):
        if not self._lgx_is_superadmin():
            self._lgx_check_cannot_edit_superadmin()
            for user in self:
                company_ids = self._lgx_extract_company_ids_from_vals(
                    vals, existing=user
                )
                if "company_id" in vals and vals["company_id"]:
                    company_ids.add(vals["company_id"])
                self._lgx_check_companies_allowed(company_ids)
                group_ids = self._lgx_extract_group_ids_from_vals(
                    vals, existing=user
                )
                self._lgx_check_no_privilege_escalation(group_ids, existing=user)
        result = super().write(vals)
        if "groups_id" in vals and not self.env.context.get("lgx_skip_superadmin_company_sync"):
            self._lgx_sync_superadmin_companies()
        # Propagate company_id change to the linked partner.
        if "company_id" in vals:
            for user in self:
                if user.company_id and user.partner_id.company_id != user.company_id:
                    user.partner_id.sudo().write({"company_id": user.company_id.id})
        return result


class ResGroups(models.Model):
    _inherit = "res.groups"

    @api.model
    def _lgx_saas_admin_ensure_partner_manager(self):
        from odoo.addons.lgx_saas_admin.hooks import _ensure_erp_implies_partner_manager
        _ensure_erp_implies_partner_manager(self.env)
        return True
