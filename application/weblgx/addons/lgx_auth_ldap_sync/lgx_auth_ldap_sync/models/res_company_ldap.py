# -*- coding: utf-8 -*-
import logging
import re

from ldap.filter import filter_format

from odoo import _, models, tools

_logger = logging.getLogger(__name__)


class CompanyLDAP(models.Model):
    _inherit = "res.company.ldap"

    def _lgx_get_ldap_list_filter(self, conf):
        filter_tmpl = conf["ldap_filter"]
        if "%s" not in filter_tmpl:
            return "(uid=*)"
        return filter_format(filter_tmpl, ["*"] * filter_tmpl.count("%s"))

    def _lgx_get_ldap_login(self, conf, ldap_entry):
        filter_tmpl = conf["ldap_filter"]
        match = re.search(r"(\w+)=%s", filter_tmpl)
        if match:
            attr = match.group(1)
            values = ldap_entry[1].get(attr)
            if values:
                return tools.ustr(values[0]).lower().strip()

        for attr in ("uid", "sAMAccountName", "cn", "mail"):
            values = ldap_entry[1].get(attr)
            if values:
                return tools.ustr(values[0]).lower().strip()
        return False

    def _lgx_create_user_from_ldap_entry(self, conf, login, ldap_entry):
        values = self._map_ldap_attributes(conf, login, ldap_entry)
        sudo_user = self.env["res.users"].sudo().with_context(no_reset_password=True)
        if conf["user"]:
            values["active"] = True
            return sudo_user.browse(conf["user"][0]).copy(default=values)
        return sudo_user.create(values)

    def _lgx_update_user_from_ldap_entry(self, conf, user, ldap_entry):
        login = tools.ustr(user.login.lower().strip())
        if hasattr(self, "_lgx_sync_user_company_from_ldap"):
            self._lgx_sync_user_company_from_ldap(conf, user.id, ldap_entry)
        values = self._map_ldap_attributes(conf, login, ldap_entry)
        user.with_context(no_reset_password=True).write({
            key: values[key]
            for key in ("name", "email", "company_id", "company_ids")
            if key in values
        })

    def _lgx_import_ldap_entry(self, conf, ldap_entry, stats):
        login = self._lgx_get_ldap_login(conf, ldap_entry)
        if not login:
            stats["skipped"] += 1
            return

        user = self.env["res.users"].sudo().search(
            [("login", "=ilike", login)],
            limit=1,
        )
        if user:
            if not user.active:
                stats["skipped"] += 1
                return
            self._lgx_update_user_from_ldap_entry(conf, user, ldap_entry)
            stats["updated"] += 1
            return

        if not conf["create_user"]:
            stats["skipped"] += 1
            return

        self._lgx_create_user_from_ldap_entry(conf, login, ldap_entry)
        stats["created"] += 1

    def _lgx_sync_users_from_conf(self, conf, stats):
        list_filter = self._lgx_get_ldap_list_filter(conf)
        entries = self._query(conf, list_filter)
        for ldap_entry in entries:
            if not ldap_entry[0]:
                continue
            try:
                with self.env.cr.savepoint():
                    self._lgx_import_ldap_entry(conf, ldap_entry, stats)
            except Exception:
                stats["errors"] += 1
                _logger.exception(
                    "LDAP: échec d'import pour %s",
                    ldap_entry[0],
                )

    def action_lgx_sync_all_users(self):
        self.check_access_rights("read")
        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
        configs = self._get_ldap_dicts()
        if not configs:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("LDAP"),
                    "message": _("Aucune configuration LDAP trouvée."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        for conf in configs:
            self._lgx_sync_users_from_conf(conf, stats)

        message = _(
            "Rechargement LDAP terminé : %(created)s créé(s), "
            "%(updated)s mis à jour, %(skipped)s ignoré(s), "
            "%(errors)s erreur(s).",
            **stats,
        )
        notification_type = "danger" if stats["errors"] else "success"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("LDAP"),
                "message": message,
                "type": notification_type,
                "sticky": stats["errors"] > 0,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }
