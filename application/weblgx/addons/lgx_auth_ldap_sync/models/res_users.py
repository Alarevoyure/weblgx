# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    lgx_from_ldap = fields.Boolean(
        string="Compte LDAP",
        default=False,
        copy=False,
        help="Utilisateur géré par le rechargement LDAP. "
             "S'il disparaît de l'annuaire, il sera désactivé.",
    )

    def action_lgx_reload_ldap_users(self):
        return self.env["res.company.ldap"].action_lgx_sync_all_users()
