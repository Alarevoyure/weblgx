from weblgx import _, api, fields, models
from weblgx.exceptions import AccessError, UserError


class WikiPage(models.Model):
    _name = "wiki.page"
    _description = "Wiki Page"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"

    name = fields.Char("Title", required=True, tracking=True)
    website_id = fields.Many2one(
        "website",
        string="Website",
        index=True,
        tracking=True,
        default=lambda self: self._wiki_infer_website() or False,
        domain=lambda self: [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", self.env.companies.ids),
        ],
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="website_id.company_id",
        store=True,
        readonly=True,
    )
    level = fields.Selection(
        [
            ("1", "Title"),
            ("2", "Subtitle"),
            ("3", "Sub-subtitle"),
            ("4", "Level 4"),
            ("5", "Level 5"),
        ],
        default="1",
        required=True,
    )
    parent_id = fields.Many2one("wiki.page", string="Parent", index=True)
    child_ids = fields.One2many("wiki.page", "parent_id", string="Children")

    has_page = fields.Boolean(
        "Has editable page",
        default=True,
        help="If disabled, node only appears in the table of contents.",
    )
    show_toc = fields.Selection(
        [
            ("default", "Selon le site"),
            ("show", "Afficher"),
            ("hide", "Masquer"),
        ],
        string="Sommaire",
        default="default",
        required=True,
        help=(
            "Prioritaire sur le paramètre Wiki du site. "
            "« Selon le site » conserve le réglage général."
        ),
    )
    show_page_nav = fields.Selection(
        [
            ("default", "Selon le site"),
            ("show", "Afficher"),
            ("hide", "Masquer"),
        ],
        string="Navigation dans la page",
        default="default",
        required=True,
        help=(
            "Prioritaire sur le paramètre Wiki du site. "
            "« Selon le site » conserve le réglage général. "
            "La navigation dans la page n'apparaît que sur les écrans larges."
        ),
    )
    # sanitize=False : comme blog.post.content — sinon data-oe-sanitize="no_block"
    # masque les zones de drop (d-none) et empêche d'ajouter des blocs tout en
    # permettant d'éditer ceux déjà présents. Réservé aux utilisateurs autorisés
    # à modifier le HTML (droits wiki + Website).
    content = fields.Html("Content", sanitize=False)
    sequence = fields.Integer(default=10)

    @api.model
    def _wiki_resolve_display_flag(self, page_choice, website_default):
        """Priorité page > site : show/hide forcent, default suit le site."""
        if page_choice == "show":
            return True
        if page_choice == "hide":
            return False
        return bool(website_default)

    _WIKI_SEQUENCE_STEP = 10

    @api.model
    def _wiki_pages_domain_for_website(self, website_id):
        if website_id:
            return [("website_id", "=", website_id)]
        return []

    @api.model
    def _wiki_is_descendant_of(self, page, ancestor):
        parent = page.parent_id
        while parent:
            if parent == ancestor:
                return True
            parent = parent.parent_id
        return False

    @api.model
    def _wiki_find_insert_index(self, pages, parent):
        parent_idx = next((i for i, page in enumerate(pages) if page.id == parent.id), None)
        if parent_idx is None:
            return len(pages)
        insert_idx = parent_idx + 1
        while insert_idx < len(pages) and self._wiki_is_descendant_of(pages[insert_idx], parent):
            insert_idx += 1
        return insert_idx

    @api.model
    def _wiki_shift_sequences_from(self, website_id, from_sequence, delta=None):
        delta = delta or self._WIKI_SEQUENCE_STEP
        domain = self._wiki_pages_domain_for_website(website_id)
        domain.append(("sequence", ">=", from_sequence))
        for page in self.search(domain, order="sequence desc, id desc"):
            page.sequence += delta

    @api.model
    def _wiki_prepare_sequence_vals(self, vals):
        if "sequence" in vals and not self.env.context.get("wiki_auto_sequence"):
            return vals

        website_id = vals.get("website_id")
        if not website_id:
            inferred = self._wiki_infer_website()
            website_id = inferred.id if inferred else False

        parent_id = vals.get("parent_id")
        level = vals.get("level") or "1"
        pages = self.search(
            self._wiki_pages_domain_for_website(website_id),
            order="sequence, id",
        )

        if parent_id:
            parent = self.browse(parent_id)
            if parent.exists():
                insert_idx = self._wiki_find_insert_index(pages, parent)
            else:
                insert_idx = len(pages)
        elif level == "1":
            insert_idx = len(pages)
        else:
            return vals

        if not pages or insert_idx >= len(pages):
            vals["sequence"] = (pages[-1].sequence + self._WIKI_SEQUENCE_STEP) if pages else self._WIKI_SEQUENCE_STEP
            return vals

        prev_page = pages[insert_idx - 1]
        next_page = pages[insert_idx]
        if next_page.sequence > prev_page.sequence + 1:
            vals["sequence"] = prev_page.sequence + 1
        else:
            new_sequence = prev_page.sequence + 1
            self._wiki_shift_sequences_from(website_id, new_sequence)
            vals["sequence"] = new_sequence
        return vals

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("to_review", "To Review"),
            ("approved", "Approved"),
            ("published", "Published"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )
    is_published = fields.Boolean(compute="_compute_is_published", store=True)
    last_published_content = fields.Html(
        "Last Published Content", readonly=True, sanitize=False
    )

    def get_backend_menu_id(self):
        """Menu backend pour le lien « modifier » du site (éditeur avec blocs)."""
        return self.env["ir.model.data"]._xmlid_to_res_id(
            "wiki_knowledge.menu_wiki_pages",
            raise_if_not_found=False,
        )

    @api.model
    def _wiki_website_allowed_for_env(self, website):
        """True si le site est utilisable sous l'utilisateur / le contexte multi-société."""
        if not website or not website.exists():
            return False
        w_company = website.company_id
        if self.env.su:
            return True
        if not w_company:
            return True
        return w_company.id in self.env.companies.ids

    @api.model
    def _wiki_infer_website(self):
        """Détermination du website sans choix utilisateur (évite fallback aléatoire backend)."""
        Website = self.env["website"]

        for key in ("default_website_id", "website_id"):
            wid = self.env.context.get(key)
            if wid:
                w = Website.browse(wid).exists()
                if self._wiki_website_allowed_for_env(w):
                    return w

        # Session / frontend / contexte sans le fallback « premier site de la base ».
        w = Website.get_current_website(fallback=False)
        if self._wiki_website_allowed_for_env(w):
            return w

        comp = self.env.company
        if comp:
            w = Website.search(
                [("company_id", "=", comp.id)], limit=1, order="sequence, id"
            )
            if self._wiki_website_allowed_for_env(w):
                return w

        if self.env.companies:
            w = Website.search(
                [("company_id", "in", self.env.companies.ids)],
                limit=1,
                order="sequence, id",
            )
            if self._wiki_website_allowed_for_env(w):
                return w

        return Website.browse()

    @api.depends("state")
    def _compute_is_published(self):
        for rec in self:
            rec.is_published = rec.state == "published"

    @api.constrains("level", "parent_id")
    def _check_level(self):
        for rec in self:
            if rec.parent_id:
                if rec.parent_id.website_id != rec.website_id:
                    raise UserError(_("Parent page must belong to the same website."))
                if int(rec.level) != int(rec.parent_id.level) + 1:
                    raise UserError(_("Level must be exactly one level deeper than parent."))
            elif rec.level != "1":
                raise UserError(_("Root nodes must be level 1."))

    @api.constrains("website_id")
    def _check_website_company(self):
        for rec in self:
            if rec.env.su or not rec.website_id:
                continue
            w_company = rec.website_id.company_id
            if not w_company:
                continue
            if w_company not in rec.env.companies:
                raise UserError(
                    _(
                        "You cannot link this wiki page to that website because its "
                        "company does not belong to your authorized companies."
                    )
                )

    def _wiki_is_reviewer(self):
        """Validateur wiki (approuver / publier / refuser) ou administrateur Weblgx."""
        u = self.env.user
        return (
            u.has_group("wiki_knowledge.group_wiki_reviewer")
            or u.has_group("wiki_knowledge.group_wiki_manager")
            or u.has_group("base.group_system")
        )

    def _check_review_rights(self):
        user = self.env.user
        if not (
            user.has_group("wiki_knowledge.group_wiki_reviewer")
            or user.has_group("wiki_knowledge.group_wiki_manager")
            or user.has_group("base.group_system")
        ):
            raise UserError(_("You are not allowed to validate wiki pages."))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(v) for v in vals_list]
        for vals in vals_list:
            st = vals.get("state") or "draft"
            if st != "draft" and not self._wiki_is_reviewer():
                raise AccessError(
                    _(
                        "Only Wiki Reviewers (or administrators) may create wiki pages "
                        "directly in this publication state."
                    )
                )
            if self.env.user.has_group("base.group_system"):
                if not vals.get("website_id"):
                    inf = self._wiki_infer_website()
                    vals["website_id"] = inf.id if inf else False
            else:
                inf = self._wiki_infer_website()
                vals["website_id"] = inf.id if inf else False
            if vals.get("parent_id") and not vals.get("level"):
                parent = self.browse(vals["parent_id"])
                if parent.exists():
                    vals["level"] = str(int(parent.level) + 1)
            if not self.env.context.get("wiki_auto_sequence"):
                vals.pop("sequence", None)
            vals = self._wiki_prepare_sequence_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("wiki_skip_state_access_check"):
            vals = dict(vals)
            if "website_id" in vals and not self.env.user.has_group("base.group_system"):
                vals.pop("website_id")
            return super().write(vals)
        vals = dict(vals)
        if "website_id" in vals and not self.env.user.has_group("base.group_system"):
            vals.pop("website_id")
        if "state" in vals:
            new_state = vals["state"]
            if self._wiki_is_reviewer():
                if new_state == "published":
                    rest = {k: v for k, v in vals.items() if k not in ("state", "last_published_content")}
                    if len(self) == 1:
                        vals.setdefault(
                            "last_published_content", vals.get("content", self.content)
                        )
                    else:
                        for rec in self:
                            merged = dict(rest)
                            snapshot = merged.pop("content", rec.content)
                            rec.with_context(wiki_skip_state_access_check=True).write(
                                {
                                    **merged,
                                    "state": "published",
                                    "last_published_content": snapshot,
                                }
                            )
                        return True
                return super().write(vals)
            if new_state != "to_review":
                raise AccessError(
                    _(
                        "Only Wiki Reviewers (or administrators) may change publication state "
                        "(Draft / Approved / Published). Use « Submit for Review » to send "
                        "your changes for validation."
                    )
                )
            for rec in self:
                if rec.state not in ("draft", "approved", "published"):
                    raise AccessError(
                        _("This page cannot be submitted for review in its current state.")
                    )
        return super().write(vals)

    def action_submit_review(self):
        for rec in self:
            if rec.state not in ("draft", "approved", "published"):
                raise UserError(_("Only draft, approved, or published pages can be submitted."))
        self.with_context(wiki_skip_state_access_check=True).write({"state": "to_review"})

    def action_approve(self):
        self._check_review_rights()
        for rec in self:
            if rec.state != "to_review":
                raise UserError(_("Only pages in 'To Review' can be approved."))
        self.with_context(wiki_skip_state_access_check=True).write({"state": "approved"})

    def action_publish(self):
        self._check_review_rights()
        for rec in self:
            if rec.state not in ("approved", "published"):
                raise UserError(_("Only approved pages can be published."))
        for rec in self:
            rec.with_context(wiki_skip_state_access_check=True).write(
                {
                    "state": "published",
                    "last_published_content": rec.content,
                }
            )

    def action_refuse(self):
        self._check_review_rights()
        for rec in self:
            if rec.state != "to_review":
                raise UserError(_("Only pages in 'To Review' can be refused."))
        self.with_context(wiki_skip_state_access_check=True).write({"state": "draft"})

    def action_back_to_draft(self):
        self._check_review_rights()
        for rec in self:
            if rec.state not in ("published", "approved"):
                raise UserError(_("Only published or approved pages can be sent back to draft."))
        self.with_context(wiki_skip_state_access_check=True).write({"state": "draft"})

    def _register_hook(self):
        """Après mise à niveau du module, retirer les anciennes ir.rule publiques dupliquées."""
        super()._register_hook()
        from weblgx.addons.wiki_knowledge.hooks import unlink_obsolete_wiki_public_ir_rules

        unlink_obsolete_wiki_public_ir_rules(self.env)
        # Rattache les contributions orphelines à une bibliothèque par site.
        if "wiki.gallery" in self.env:
            self.env["wiki.gallery"]._migrate_orphan_items()
