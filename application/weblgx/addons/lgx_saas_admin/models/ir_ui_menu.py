# -*- coding: utf-8 -*-
from weblgx import api, models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _visible_menu_ids(self, debug=False):
        """Return the ids of the menu items visible to the user.

        A SuperAdmin keeps the technical features group
        (``base.group_no_one``) active even outside developer mode, so the
        technical menus (Translations, Gamification Tools, Technical) remain
        visible without having to enable the developer mode.
        """
        if not debug and self.env.user.has_group("lgx_saas_admin.group_superadmin"):
            debug = True
        return super()._visible_menu_ids(debug=debug)
