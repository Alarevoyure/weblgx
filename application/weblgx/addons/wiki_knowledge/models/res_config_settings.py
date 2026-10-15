from weblgx import _, fields, models
from weblgx.exceptions import AccessError, UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wiki_border_color = fields.Char(
        related="website_id.wiki_border_color",
        readonly=False,
    )
    wiki_show_toc = fields.Boolean(
        related="website_id.wiki_show_toc",
        readonly=False,
    )
    wiki_show_page_nav = fields.Boolean(
        related="website_id.wiki_show_page_nav",
        readonly=False,
    )
    wiki_show_site_header = fields.Boolean(
        related="website_id.wiki_show_site_header",
        readonly=False,
    )
    wiki_show_site_footer = fields.Boolean(
        related="website_id.wiki_show_site_footer",
        readonly=False,
    )
    wiki_show_footer = fields.Boolean(
        related="website_id.wiki_show_footer",
        readonly=False,
    )
    wiki_review_email = fields.Char(
        string="Email de validation des articles",
        related="website_id.wiki_review_email",
        readonly=False,
    )

    def _compute_display_name(self):
        # Base implementation searches ir.actions.act_window without sudo;
        # Wiki Managers do not have ACL on that model.
        action = self.env["ir.actions.act_window"].sudo().search(
            [("res_model", "=", self._name)],
            limit=1,
        )
        name = action.name or _("Settings")
        for record in self:
            record.display_name = name

    def cancel(self):
        actions = self.env["ir.actions.act_window"].sudo().search(
            [("res_model", "=", self._name)],
            limit=1,
        )
        if actions:
            return actions.read()[0]
        return {}

    def execute(self):
        """Allow Wiki Managers to save Wiki display settings (not full admin)."""
        self.ensure_one()
        if self.env.is_admin():
            return super().execute()

        if not self.env.user.has_group("wiki_knowledge.group_wiki_manager"):
            raise AccessError(_("Only administrators can change the settings"))

        website = self.website_id
        if not website:
            raise UserError(_("Please select a website."))

        # Write only wiki fields — never install modules or touch other settings.
        website.write({
            "wiki_border_color": self.wiki_border_color,
            "wiki_show_toc": self.wiki_show_toc,
            "wiki_show_page_nav": self.wiki_show_page_nav,
            "wiki_show_site_header": self.wiki_show_site_header,
            "wiki_show_site_footer": self.wiki_show_site_footer,
            "wiki_show_footer": self.wiki_show_footer,
            "wiki_review_email": (self.wiki_review_email or "").strip() or False,
        })
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
