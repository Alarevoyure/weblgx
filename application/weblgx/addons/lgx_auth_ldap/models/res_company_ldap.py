# -*- coding: utf-8 -*-
import logging
import re

import ldap.dn

from odoo import models, tools

_logger = logging.getLogger(__name__)

_ORG_ATTRS = ("o", "organizationName", "company")


class CompanyLDAP(models.Model):
    _inherit = "res.company.ldap"

    def _lgx_get_ldap_attribute(self, ldap_attrs, attr_name):
        values = ldap_attrs.get(attr_name)
        if not values:
            return False
        value = tools.ustr(values[0]).strip()
        return value or False

    def _lgx_get_organization_name_from_dn(self, dn):
        if not dn:
            return False
        try:
            for rdn in ldap.dn.explode_dn(dn):
                for rdn_part in ldap.dn.explode_rdn(rdn):
                    attr, _, value = rdn_part.partition("=")
                    if attr.lower() == "o" and value:
                        return tools.ustr(value).strip()
        except ldap.DECODING_ERROR:
            pass
        match = re.search(r"(?:^|,)o=([^,]+)", dn, flags=re.IGNORECASE)
        if match:
            return tools.ustr(match.group(1)).strip()
        return False

    def _lgx_get_organization_name(self, ldap_entry):
        """Return Organization Name from LDAP entry attributes or DN."""
        _, ldap_attrs = ldap_entry
        for attr_name in _ORG_ATTRS:
            organization_name = self._lgx_get_ldap_attribute(ldap_attrs, attr_name)
            if organization_name:
                return organization_name
        return self._lgx_get_organization_name_from_dn(ldap_entry[0])

    def _lgx_get_company_from_organization(self, organization_name, fallback_company_id):
        if not organization_name:
            return self.env["res.company"].sudo().browse(fallback_company_id)

        company = self.env["res.company"].sudo().search(
            [("name", "=ilike", organization_name)],
            limit=1,
        )
        if company:
            return company

        _logger.warning(
            "LDAP: aucune société Web@LGX pour l'Organization Name %r, "
            "utilisation de la société LDAP par défaut (id=%s).",
            organization_name,
            fallback_company_id,
        )
        return self.env["res.company"].sudo().browse(fallback_company_id)

    def _lgx_resolve_company_from_ldap_entry(self, conf, ldap_entry):
        organization_name = self._lgx_get_organization_name(ldap_entry)
        return self._lgx_get_company_from_organization(
            organization_name,
            conf["company"][0],
        )

    def _lgx_sync_user_company_from_ldap(self, conf, user_id, ldap_entry):
        company = self._lgx_resolve_company_from_ldap_entry(conf, ldap_entry)
        user = self.env["res.users"].sudo().browse(user_id)
        if user.company_id == company:
            return
        user.write({
            "company_id": company.id,
            "company_ids": [(6, 0, company.ids)],
        })
        _logger.info(
            "LDAP: société de %s mise à jour vers %r (Organization Name).",
            user.login,
            company.name,
        )

    def _map_ldap_attributes(self, conf, login, ldap_entry):
        data = super()._map_ldap_attributes(conf, login, ldap_entry)
        company = self._lgx_resolve_company_from_ldap_entry(conf, ldap_entry)
        data["company_id"] = company.id
        data["company_ids"] = [(6, 0, company.ids)]
        return data

    def _get_or_create_user(self, conf, login, ldap_entry):
        login = tools.ustr(login.lower().strip())
        self.env.cr.execute(
            "SELECT id, active FROM res_users WHERE lower(login)=%s",
            (login,),
        )
        res = self.env.cr.fetchone()
        if res and res[1]:
            self._lgx_sync_user_company_from_ldap(conf, res[0], ldap_entry)
        user_id = super()._get_or_create_user(conf, login, ldap_entry)
        if user_id and "lgx_from_ldap" in self.env["res.users"]._fields:
            user = self.env["res.users"].sudo().browse(user_id)
            if user.exists() and not user.lgx_from_ldap:
                user.write({"lgx_from_ldap": True})
        return user_id
