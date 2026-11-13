import re

from weblgx import _, api, fields, models
from weblgx.exceptions import AccessError, UserError
from weblgx.http import request
from weblgx.tools.misc import html_escape

# Champs Wiki modifiables par les Wiki Managers (sans être designer site).
_WIKI_SETTINGS_FIELDS = frozenset({
    "wiki_border_color",
    "wiki_show_toc",
    "wiki_show_page_nav",
    "wiki_show_view_count",
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
    "wiki_privacy_policy_url",
    "wiki_writing_help_url",
    "wiki_footer",
    "wiki_meta_title",
    "wiki_meta_description",
    "wiki_meta_keywords",
    "wiki_meta_og_img",
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
    wiki_show_view_count = fields.Boolean(
        string="Show article view count",
        default=True,
        help="Afficher le nombre de vues en bas des articles de la bibliothèque Wiki.",
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
    wiki_privacy_policy_url = fields.Char(
        string="URL Politique de protection des données",
        help=(
            "Lien vers la page « Politique de protection des données » "
            "affiché avant le dépôt d'une contribution (bibliothèque Wiki). "
            "Propre à chaque site. Exemple : /privacy ou https://…"
        ),
    )
    wiki_writing_help_url = fields.Char(
        string="URL Aide à la rédaction",
        help=(
            "Lien vers la page d'aide à la rédaction, proposé avant le dépôt "
            "d'une contribution (bibliothèque Wiki). "
            "Propre à chaque site. Exemple : /wiki/aide ou https://…"
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

    # --- SEO du Wiki ---------------------------------------------------------
    # Métadonnées SEO uniformes appliquées à toutes les pages du Wiki du site
    # (mêmes informations pour toutes les pages, par site).
    wiki_meta_title = fields.Char(
        string="Meta title",
        translate=True,
        help=(
            "Titre SEO appliqué à toutes les pages du Wiki (balise <title> et "
            "Open Graph). Laissez vide pour conserver le titre par défaut : "
            "nom de la page ou de l'article, suivi du nom du site."
        ),
    )
    wiki_meta_description = fields.Text(
        string="Meta description",
        translate=True,
        help=(
            "Description SEO appliquée à toutes les pages du Wiki (balise "
            "description et Open Graph)."
        ),
    )
    wiki_meta_keywords = fields.Char(
        string="Meta keywords",
        translate=True,
        help=(
            "Mots-clés séparés par des virgules, appliqués à toutes les pages "
            "du Wiki."
        ),
    )
    wiki_meta_og_img = fields.Binary(
        string="Image de partage social",
        attachment=True,
        help=(
            "Image Open Graph utilisée pour le partage des pages du Wiki. "
            "Si vide, l'image de partage (ou le logo) du site est utilisée."
        ),
    )

    def get_website_meta(self):
        """Métadonnées SEO des pages Wiki (même rendu que website.seo.metadata).

        Le modèle ``website`` n'hérite pas du mixin ``website.seo.metadata`` ;
        on fournit ici les balises OpenGraph / Twitter et la description lues
        dans les réglages « SEO du Wiki », appliquées uniformément à toutes
        les pages Wiki du site.
        """
        self.ensure_one()
        title = (self.wiki_meta_title or "").strip()
        description = (self.wiki_meta_description or "").strip()
        if self.wiki_meta_og_img:
            og_image = self.image_url(self, "wiki_meta_og_img")
        else:
            og_image = self.image_url(
                self,
                "social_default_image" if self.has_social_default_image else "logo",
            )
        root_url = (self.get_base_url() or "").rstrip("/")
        path = request.httprequest.path if request else ""
        if root_url and not og_image.startswith(("http://", "https://")):
            og_image = f"{root_url}{og_image}"
        opengraph_meta = {
            "og:type": "website",
            "og:site_name": self.name,
            "og:url": f"{root_url}{path}",
            "og:image": og_image,
        }
        twitter_meta = {
            "twitter:card": "summary_large_image",
            "twitter:image": og_image,
        }
        if title:
            opengraph_meta["og:title"] = title
            twitter_meta["twitter:title"] = title
        if description:
            opengraph_meta["og:description"] = description
            twitter_meta["twitter:description"] = description
        return {
            "opengraph_meta": opengraph_meta,
            "twitter_meta": twitter_meta,
            "meta_description": description or False,
        }

    def write(self, vals):
        """Wiki Managers may update wiki display settings only (not full website)."""
        if vals and "wiki_review_email" in vals:
            vals = dict(vals)
            email = (vals.get("wiki_review_email") or "").strip()
            if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                raise UserError(_("L'email de validation des articles n'est pas valide."))
            vals["wiki_review_email"] = email or False
        url_fields = {
            "wiki_privacy_policy_url": _(
                "L'URL de la Politique de protection des données "
                "n'est pas valide (chemin /… ou URL http(s))."
            ),
            "wiki_writing_help_url": _(
                "L'URL d'aide à la rédaction n'est pas valide "
                "(chemin /… ou URL http(s))."
            ),
        }
        for field_name, error_msg in url_fields.items():
            if vals and field_name in vals:
                vals = dict(vals)
                url = (vals.get(field_name) or "").strip()
                if url and not re.match(
                    r"^(https?://|/|#)[^\s]*$",
                    url,
                    re.IGNORECASE,
                ):
                    raise UserError(error_msg)
                vals[field_name] = url or False
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
                        "Wiki Managers can only change Wiki settings "
                        "(display, gallery and SEO)."
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
