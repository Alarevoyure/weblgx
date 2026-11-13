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
    wiki_show_view_count = fields.Boolean(
        related="website_id.wiki_show_view_count",
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
    wiki_privacy_policy_url = fields.Char(
        string="URL Politique de protection des données",
        related="website_id.wiki_privacy_policy_url",
        readonly=False,
    )
    wiki_writing_help_url = fields.Char(
        string="URL Aide à la rédaction",
        related="website_id.wiki_writing_help_url",
        readonly=False,
    )
    wiki_meta_title = fields.Char(
        string="Meta title",
        related="website_id.wiki_meta_title",
        readonly=False,
    )
    wiki_meta_description = fields.Text(
        string="Meta description",
        related="website_id.wiki_meta_description",
        readonly=False,
    )
    wiki_meta_keywords = fields.Char(
        string="Meta keywords",
        related="website_id.wiki_meta_keywords",
        readonly=False,
    )
    wiki_meta_og_img = fields.Binary(
        string="Image de partage social",
        related="website_id.wiki_meta_og_img",
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
            "wiki_show_view_count": self.wiki_show_view_count,
            "wiki_show_site_header": self.wiki_show_site_header,
            "wiki_show_site_footer": self.wiki_show_site_footer,
            "wiki_show_footer": self.wiki_show_footer,
            "wiki_review_email": (self.wiki_review_email or "").strip() or False,
            "wiki_privacy_policy_url": (
                (self.wiki_privacy_policy_url or "").strip() or False
            ),
            "wiki_writing_help_url": (
                (self.wiki_writing_help_url or "").strip() or False
            ),
            "wiki_meta_title": (self.wiki_meta_title or "").strip() or False,
            "wiki_meta_description": (
                (self.wiki_meta_description or "").strip() or False
            ),
            "wiki_meta_keywords": (
                (self.wiki_meta_keywords or "").strip() or False
            ),
            "wiki_meta_og_img": self.wiki_meta_og_img or False,
        })
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
