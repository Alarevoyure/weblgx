import re

from weblgx import _, api, fields, models
from weblgx.exceptions import AccessError, UserError
from weblgx.tools.misc import html_escape

# Champs Wiki modifiables par les Wiki Managers (sans être designer site).
_WIKI_SETTINGS_FIELDS = frozenset({
    "wiki_border_color",
    "wiki_show_toc",
    "wiki_show_page_nav",
    "wiki_header",
    "wiki_logo",
    "wiki_logo_height",
    "wiki_logo_height_scrolled",
    "wiki_header_brand_type",
    "wiki_header_brand_name",
    "wiki_header_scroll_effect",
    "wiki_show_site_header",
    "wiki_show_site_footer",
    "wiki_show_footer",
    "wiki_review_email",
    "wiki_footer",
    "wiki_header_show_logo",
    "wiki_header_show_search",
    "wiki_header_show_signin",
    "wiki_header_show_menu",
})


class Website(models.Model):
    _inherit = "website"

    wiki_border_color = fields.Char(
        string="Wiki border color",
        default="#000000",
        help="Couleur des bordures du wiki (sommaire, séparateurs).",
    )
    wiki_show_toc = fields.Boolean(
        string="Show wiki table of contents",
        default=True,
        help="Afficher le panneau Sommaire sur la page Wiki.",
    )
    wiki_show_page_nav = fields.Boolean(
        string="Show in-page navigation (desktop)",
        default=True,
        help=(
            "Afficher une aide à la navigation dans la page (liste des titres) "
            "sur la droite du contenu, uniquement sur les écrans larges."
        ),
    )
    wiki_show_site_header = fields.Boolean(
        string="Show site header on Wiki",
        default=True,
        help=(
            "Si décoché, le header du site (logo + menu) est masqué sur /wiki. "
            "Seul le Header Wiki reste visible."
        ),
    )
    wiki_show_site_footer = fields.Boolean(
        string="Show site footer on Wiki",
        default=True,
        help=(
            "Si décoché, le footer du site est masqué sur /wiki. "
            "Le Footer Wiki peut rester visible."
        ),
    )
    wiki_review_email = fields.Char(
        string="Email de validation des articles",
        help=(
            "Adresse prévenue lorsqu'un article de la Bibliothèque Wiki "
            "est déposé pour validation. Propre à chaque site."
        ),
    )
    wiki_show_footer = fields.Boolean(
        string="Show Wiki footer",
        default=True,
        help=(
            "Si décoché, le Footer Wiki est masqué sur /wiki. "
            "Le footer du site peut rester visible."
        ),
    )
    wiki_header_show_logo = fields.Boolean(
        string="Wiki header: show logo",
        default=False,
        help="Afficher le logo Wiki dans le Header Wiki.",
    )
    wiki_header_show_search = fields.Boolean(
        string="Wiki header: show search",
        default=False,
        help="Afficher le bouton de recherche dans le Header Wiki.",
    )
    wiki_header_show_signin = fields.Boolean(
        string="Wiki header: show sign in",
        default=False,
        help="Afficher Connexion / compte dans le Header Wiki.",
    )
    wiki_header_show_menu = fields.Boolean(
        string="Wiki header: show pages menu",
        default=True,
        help="Afficher le menu de navigation des pages Wiki dans le Header Wiki.",
    )
    wiki_logo = fields.Binary(
        string="Wiki Header Logo",
        attachment=True,
        help=(
            "Logo du Header Wiki, indépendant du logo du site. "
            "Modifiable en double-cliquant sur le logo en mode édition. "
            "Propre à chaque site (SaaS)."
        ),
    )
    wiki_header_brand_type = fields.Selection(
        selection=[
            ("image", "Image"),
            ("text", "Text"),
        ],
        string="Wiki header brand type",
        default="image",
        required=True,
        help="Afficher le logo Wiki en image ou en texte (par site).",
    )
    wiki_header_brand_name = fields.Char(
        string="Wiki header brand text",
        translate=True,
        help="Texte affiché lorsque le logo Wiki est en mode Texte.",
    )
    wiki_logo_height = fields.Integer(
        string="Wiki logo height",
        default=40,
        help="Hauteur du logo / marque Wiki en pixels (par site).",
    )
    wiki_logo_height_scrolled = fields.Integer(
        string="Wiki logo height (scrolled)",
        default=40,
        help="Hauteur du logo Wiki une fois le Header Wiki défilé (par site).",
    )
    wiki_header_scroll_effect = fields.Selection(
        selection=[
            ("standard", "Standard"),
            ("scroll", "Scroll"),
            ("fixed", "Fixed"),
            ("disappears", "Disappears"),
            ("fade-out", "Fade Out"),
        ],
        string="Wiki header scroll effect",
        default="standard",
        required=True,
        help="Effet de défilement du Header Wiki (indépendant du Header du site).",
    )
    # sanitize=False : comme le contenu wiki — autorise les blocs du site web.
    wiki_header = fields.Html(
        string="Header Wiki",
        sanitize=False,
        translate=True,
        help=(
            "Header du portail Wiki (pleine largeur, sous le header du site). "
            "Éditable via « Modifier » sur /wiki — blocs autorisés. "
            "Commun à toutes les pages Wiki de ce site (multi-site)."
        ),
    )
    wiki_footer = fields.Html(
        string="Footer Wiki",
        sanitize=False,
        translate=True,
        help=(
            "Footer du portail Wiki (pleine largeur, au-dessus du footer du site). "
            "Éditable via « Modifier » sur /wiki — liens et blocs propres au Wiki. "
            "Commun à toutes les pages Wiki de ce site (multi-site)."
        ),
    )

    def write(self, vals):
        """Wiki Managers may update wiki display settings only (not full website)."""
        if vals and "wiki_review_email" in vals:
            vals = dict(vals)
            email = (vals.get("wiki_review_email") or "").strip()
            if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                raise UserError(_("L'email de validation des articles n'est pas valide."))
            vals["wiki_review_email"] = email or False
        if (
            not self.env.su
            and vals
            and self.env.user.has_group("wiki_knowledge.group_wiki_manager")
            and not self.env.user.has_group("website.group_website_designer")
            and not self.env.user.has_group("base.group_system")
        ):
            forbidden = set(vals) - _WIKI_SETTINGS_FIELDS
            if forbidden:
                raise AccessError(
                    _(
                        "Wiki Managers can only change Wiki display settings "
                        "(table of contents, borders, in-page navigation, header, footer)."
                    )
                )
        return super().write(vals)

    @api.model
    def _wiki_default_header_html(self, title):
        safe = html_escape(title or "Wiki")
        return (
            '<section class="s_text_block pt16 pb16" data-snippet="s_text_block" data-name="Titre">'
            '<div class="container">'
            f'<h1 class="mb-0">{safe}</h1>'
            "</div></section>"
        )

    @api.model
    def _wiki_ensure_headers(self):
        """Initialise une zone de titre par site si elle est encore vide (multi-site)."""
        Website = self.sudo()
        WikiPage = self.env["wiki.page"].sudo()
        for website in Website.search([]):
            raw = website.wiki_header or ""
            if raw.strip():
                continue
            title = "Wiki"
            root = WikiPage.search(
                [
                    ("website_id", "=", website.id),
                    ("has_page", "=", True),
                    ("parent_id", "=", False),
                    ("name", "ilike", "Wiki%"),
                ],
                limit=1,
                order="sequence, id",
            )
            if root:
                title = root.name
            website.wiki_header = self._wiki_default_header_html(title)

    @api.model
    def _wiki_default_footer_html(self):
        return (
            '<section class="s_text_block pt32 pb16" data-snippet="s_text_block" '
            'data-name="Liens Wiki">'
            '<div class="container">'
            '<div class="row">'
            '<div class="col-lg-4 pt16 pb16">'
            '<h5 class="mb-3">Wiki</h5>'
            '<ul class="list-unstyled">'
            '<li class="py-1"><a href="/wiki">Accueil du Wiki</a></li>'
            "</ul>"
            "</div></div></div></section>"
        )

    @api.model
    def _wiki_ensure_footers(self):
        """Initialise le Footer Wiki par site s'il est encore vide (multi-site)."""
        for website in self.sudo().search([]):
            raw = website.wiki_footer or ""
            if raw.strip():
                continue
            website.wiki_footer = self._wiki_default_footer_html()

    @api.model
    def _wiki_ensure_logos(self):
        """Initialise logo / texte Wiki si encore vides (copie une seule fois, multi-site)."""
        for website in self.sudo().search([]):
            vals = {}
            if not website.wiki_logo and website.logo:
                vals["wiki_logo"] = website.logo
            if not (website.wiki_header_brand_name or "").strip():
                vals["wiki_header_brand_name"] = website.name or "Wiki"
            if not website.wiki_logo_height:
                vals["wiki_logo_height"] = 40
            if not website.wiki_logo_height_scrolled:
                vals["wiki_logo_height_scrolled"] = website.wiki_logo_height or 40
            if vals:
                website.write(vals)

    def _register_hook(self):
        super()._register_hook()
        # Idempotent : ne remplit que les en-têtes / logos encore vides.
        try:
            self._wiki_ensure_headers()
            self._wiki_ensure_footers()
            self._wiki_ensure_logos()
        except Exception:
            # Évite de bloquer le registry si le champ n'est pas encore migré.
            pass
