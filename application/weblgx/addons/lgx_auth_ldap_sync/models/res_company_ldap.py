# -*- coding: utf-8 -*-
import logging
import re

from odoo import _, models, tools
from odoo import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class CompanyLDAP(models.Model):
    _inherit = "res.company.ldap"

    def _lgx_get_ldap_list_filter(self, conf):
        filter_tmpl = conf["ldap_filter"]
        if "%s" not in filter_tmpl:
            return "(uid=*)"
        # Remplacer le placeholder par le joker LDAP, sans filter_format
        # qui échapperait l'étoile en valeur littérale.
        return filter_tmpl.replace("%s", "*")

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
        values["lgx_from_ldap"] = True
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
        values["lgx_from_ldap"] = True
        values["active"] = True
        user.with_context(no_reset_password=True).write({
            key: values[key]
            for key in ("name", "email", "company_id", "company_ids", "lgx_from_ldap", "active")
            if key in values
        })

    def _lgx_import_ldap_entry(self, conf, ldap_entry, stats, ldap_logins):
        login = self._lgx_get_ldap_login(conf, ldap_entry)
        if not login:
            stats["skipped"] += 1
            return

        ldap_logins.add(login)
        user = self.env["res.users"].sudo().with_context(active_test=False).search(
            [("login", "=ilike", login)],
            limit=1,
        )
        if user:
            self._lgx_update_user_from_ldap_entry(conf, user, ldap_entry)
            stats["updated"] += 1
            return

        if not conf["create_user"]:
            stats["skipped"] += 1
            return

        self._lgx_create_user_from_ldap_entry(conf, login, ldap_entry)
        stats["created"] += 1

    def _lgx_sync_users_from_conf(self, conf, stats, ldap_logins):
        list_filter = self._lgx_get_ldap_list_filter(conf)
        entries = self._query(conf, list_filter)
        for ldap_entry in entries:
            if not ldap_entry[0]:
                continue
            try:
                with self.env.cr.savepoint():
                    self._lgx_import_ldap_entry(conf, ldap_entry, stats, ldap_logins)
            except Exception:
                stats["errors"] += 1
                _logger.exception(
                    "LDAP: échec d'import pour %s",
                    ldap_entry[0],
                )

    def _lgx_protected_user_ids(self):
        """Accounts that must never be deactivated by LDAP sync."""
        ids = {SUPERUSER_ID}
        for xmlid in ("base.user_root", "base.user_admin"):
            user = self.env.ref(xmlid, raise_if_not_found=False)
            if user:
                ids.add(user.id)
        group_super = self.env.ref(
            "lgx_saas_admin.group_superadmin",
            raise_if_not_found=False,
        )
        if group_super:
            ids.update(group_super.users.ids)
        return ids

    def _lgx_operator_is_superadmin(self):
        if self.env.su or self.env.uid == SUPERUSER_ID:
            return True
        return self.env.user.has_group("lgx_saas_admin.group_superadmin")

    def _lgx_deactivate_missing_ldap_users(self, ldap_logins, stats):
        """Archive LDAP-managed users absent from the directory."""
        Users = self.env["res.users"].sudo()
        domain = [
            ("active", "=", True),
            ("share", "=", False),
            ("lgx_from_ldap", "=", True),
        ]
        protected = self._lgx_protected_user_ids()
        if protected:
            domain.append(("id", "not in", list(protected)))

        if not self._lgx_operator_is_superadmin():
            domain.append(("company_ids", "in", self.env.user.company_ids.ids))

        candidates = Users.search(domain)
        to_deactivate = candidates.filtered(
            lambda u: tools.ustr(u.login).lower().strip() not in ldap_logins
        )
        if not to_deactivate:
            return

        to_deactivate.write({"active": False})
        stats["deactivated"] = len(to_deactivate)
        _logger.info(
            "LDAP: désactivation de %s utilisateur(s) absent(s) de l'annuaire : %s",
            len(to_deactivate),
            ", ".join(to_deactivate.mapped("login")),
        )

    def action_lgx_sync_all_users(self):
        self.check_access_rights("read")
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "deactivated": 0,
        }
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

        ldap_logins = set()
        for conf in configs:
            self._lgx_sync_users_from_conf(conf, stats, ldap_logins)

        try:
            with self.env.cr.savepoint():
                self._lgx_deactivate_missing_ldap_users(ldap_logins, stats)
        except Exception:
            stats["errors"] += 1
            _logger.exception("LDAP: échec de la désactivation des comptes absents")

        message = _(
            "Rechargement LDAP terminé : %(created)s créé(s), "
            "%(updated)s mis à jour, %(deactivated)s désactivé(s) (absents de LDAP), "
            "%(skipped)s ignoré(s), %(errors)s erreur(s).",
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
