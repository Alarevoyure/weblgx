# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def action_lgx_reload_ldap_users(self):
        return self.env["res.company.ldap"].action_lgx_sync_all_users()
