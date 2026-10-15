import re
from urllib.parse import quote

from markupsafe import Markup, escape

from weblgx import http
from weblgx.http import request
from weblgx.osv.expression import AND, OR
from weblgx.tools import html2plaintext

_GALLERY_ATTR_RE = re.compile(
    r"""data-gallery-id\s*=\s*["'](\d+)["']""",
    re.IGNORECASE,
)


class WikiPortal(http.Controller):

    def _wiki_current_website(self):
        website = getattr(request, "website", False)
        if website:
            return website
        return request.env["website"].get_current_website()

    def _wiki_can_see_draft(self):
        return request.env.user.has_group("wiki_knowledge.group_wiki_user")

    def _wiki_company_domain(self):
        """Périmètre société pour lister les pages wiki (portail)."""
        user = request.env.user
        if user._is_public():
            website = self._wiki_current_website()
            if website and website.company_id:
                return ["|", ("company_id", "=", False), ("company_id", "=", website.company_id.id)]
            # Site sans société explicite : pages sans société seulement
            return [("company_id", "=", False)]
        company_ids = user._get_company_ids()
        if not company_ids:
            return [("company_id", "=", False)]
        return ["|", ("company_id", "=", False), ("company_id", "in", list(company_ids))]

    def _wiki_pages_domain(self):
        current_website = self._wiki_current_website()
        website_domain = ["|", ("website_id", "=", current_website.id), ("website_id", "=", False)]
        company_domain = self._wiki_company_domain()
        merged = AND([website_domain, company_domain])
        if self._wiki_can_see_draft():
            return merged
        return AND([merged,
            [
            "|",
            ("state", "=", "published"),
            "&",
            ("state", "in", ["to_review", "approved"]),
            ("last_published_content", "!=", False),
        ],
        ])

    def _wiki_can_front_edit(self):
        user = request.env.user
        return (
            user.has_group("wiki_knowledge.group_wiki_user")
            or user.has_group("wiki_knowledge.group_wiki_reviewer")
            or user.has_group("wiki_knowledge.group_wiki_manager")
            or user.has_group("base.group_system")
        )

    def _wiki_portal_company_allows_page(self, page):
        """Contrôle société pour les écritures explicites (API) et cohérence site."""
        if not page or not page.exists():
            return False
        u = request.env.user
        if u.has_group("base.group_system"):
            return True
        cid = page.company_id.id if page.company_id else False
        if not cid:
            return True  # Wikis sans société : visibles de tous les contextes métier portail affichés
        if u._is_public():
            website = self._wiki_current_website()
            return bool(website and website.company_id and website.company_id.id == cid)
        return cid in u._get_company_ids()

    def _wiki_visible_body_html(self, page):
        """Contenu HTML affichable pour la recherche (respecte brouillon / publié)."""
        if not page:
            return ""
        if self._wiki_can_see_draft():
            return page.content or page.last_published_content or ""
        if page.state == "published":
            # Hors rédaction : défense en profondeur — le public ne doit pas voir « content »
            # (brouillon) tant qu’un validateur n’a pas rejoué « Publish » et copié en last_*.
            return page.last_published_content or page.content or ""
        return page.last_published_content or page.content or ""

    def _wiki_search_domain(self, term):
        """Domaine de recherche (pages visibles + has_page), titre et corps."""
        t = (term or "").strip()
        base = self._wiki_pages_domain()
        has_page = [("has_page", "=", True)]
        if self._wiki_can_see_draft():
            text_or = OR(
                [
                    [("name", "ilike", t)],
                    [("content", "ilike", t)],
                    [("last_published_content", "ilike", t)],
                ]
            )
        else:
            pub_body = AND(
                [
                    [("state", "=", "published")],
                    OR([[("content", "ilike", t)], [("last_published_content", "ilike", t)]]),
                ]
            )
            text_or = OR([[("name", "ilike", t)], pub_body, [("last_published_content", "ilike", t)]])
        return AND([base, has_page, text_or])

    def _wiki_text_snippet(self, plain, term, width=220):
        """Extrait autour du terme, sinon le début du texte."""
        plain = " ".join((plain or "").split())
        t = (term or "").strip().lower()
        snippet = plain[:width]
        if len(plain) > width:
            snippet += "…"
        if t and plain and t in plain.lower():
            idx = plain.lower().index(t)
            start = max(0, idx - 40)
            chunk = plain[start : start + 160]
            if start > 0:
                chunk = "…" + chunk
            if start + 160 < len(plain):
                chunk += "…"
            snippet = chunk
        return snippet

    def _wiki_with_query(self, url, key, value):
        url = url or "/"
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}{key}={value}"

    def _wiki_articles_domain(self, term=None):
        """Articles publiés des bibliothèques du site courant."""
        website = self._wiki_current_website()
        if not website:
            return [("id", "=", 0)]
        base = AND(
            [
                [("website_id", "=", website.id)],
                self._wiki_company_domain(),
                [
                    ("state", "=", "published"),
                    ("gallery_id", "!=", False),
                    ("gallery_id.active", "=", True),
                ],
            ]
        )
        t = (term or "").strip()
        if not t:
            return base
        return AND([base, OR([[("name", "ilike", t)], [("text", "ilike", t)]])])

    def _wiki_visible_article(self, article_id):
        try:
            article_id = int(article_id)
        except (TypeError, ValueError):
            return request.env["wiki.gallery.item"]
        return (
            request.env["wiki.gallery.item"]
            .sudo()
            .search(
                AND([self._wiki_articles_domain(), [("id", "=", article_id)]]),
                limit=1,
            )
        )

    def _wiki_gallery_host_urls(self, gallery_ids):
        """URL publique de la page qui embarque chaque bibliothèque."""
        website = self._wiki_current_website()
        wanted = {int(gid) for gid in gallery_ids if gid}
        found = {}
        if not website or not wanted:
            return found

        views = (
            request.env["ir.ui.view"]
            .sudo()
            .search(
                [
                    ("type", "=", "qweb"),
                    ("website_id", "in", [False, website.id]),
                    ("arch_db", "ilike", "data-gallery-id"),
                ]
            )
        )
        gallery_by_view = {}
        for view in views:
            ids = {int(match) for match in _GALLERY_ATTR_RE.findall(view.arch or "")}
            ids &= wanted
            if ids:
                gallery_by_view[view.id] = ids
        if gallery_by_view:
            pages = (
                request.env["website.page"]
                .sudo()
                .search(
                    [
                        ("view_id", "in", list(gallery_by_view)),
                        ("is_published", "=", True),
                        "|",
                        ("website_id", "=", website.id),
                        ("website_id", "=", False),
                    ]
                )
            )
            # Page propre au site avant une page générique.
            for page in pages.sorted(key=lambda rec: (not rec.website_id, rec.id)):
                url = page.url or "/"
                if not url.startswith("/"):
                    url = "/" + url
                for gid in gallery_by_view.get(page.view_id.id, ()):
                    found.setdefault(gid, url)

        missing = wanted - set(found)
        if missing:
            wiki_pages = request.env["wiki.page"].sudo().search(
                AND(
                    [
                        self._wiki_pages_domain(),
                        [
                            "|",
                            ("content", "ilike", "data-gallery-id"),
                            ("last_published_content", "ilike", "data-gallery-id"),
                        ],
                    ]
                )
            )
            for page in wiki_pages:
                html = self._wiki_visible_body_html(page) or ""
                for gid_s in _GALLERY_ATTR_RE.findall(html):
                    gid = int(gid_s)
                    if gid in missing:
                        found.setdefault(gid, f"/wiki?page_id={page.id}")
        return found

    def _wiki_article_public_url(self, item_id):
        return f"/wiki/article/{int(item_id)}"

    def _wiki_article_image_url(self, item_id):
        """Photo à la taille stockée (le champ « image » est sinon réduit à 1024 px)."""
        return f"/web/image/wiki.gallery.item/{int(item_id)}/image/1920x1920"

    def _wiki_article_media(self, item):
        """URL de lecture, seulement si un type audio ou vidéo est enregistré."""
        kind = item._media_kind()
        filename = (item.media_filename or "").strip()
        if not kind or not filename:
            return "", ""
        return kind, (
            f"/web/content/wiki.gallery.item/{int(item.id)}/media/{quote(filename)}"
        )

    def _wiki_article_payload(self, item):
        gallery_name = (item.gallery_id.name or "").strip()
        hosts = self._wiki_gallery_host_urls([item.gallery_id.id])
        back_url = hosts.get(item.gallery_id.id) or "/wiki"
        media_kind, media_url = self._wiki_article_media(item)
        return {
            "name": (item.name or "").strip() or "Sans titre",
            "meta": gallery_name,
            "text": Markup(item._text_as_html() or ""),
            "image_url": self._wiki_article_image_url(item.id),
            "media_kind": media_kind,
            "media_url": media_url,
            "contributor_name": (item.contributor_name or "").strip(),
            "view_count": int(item.view_count or 0),
            "back_url": back_url,
            "back_label": "Retour à la bibliothèque" if back_url != "/wiki" else "Retour au wiki",
        }

    def _wiki_article_rows(self, items, term):
        """Résultats de recherche pour les articles de bibliothèque."""
        rows = []
        for item in items:
            gallery_name = (item.gallery_id.name or "").strip()
            rows.append(
                {
                    "title": (item.name or "").strip() or "Sans titre",
                    "meta": f"Article — {gallery_name}" if gallery_name else "Article",
                    "snippet": self._wiki_text_snippet(html2plaintext(item.text or ""), term),
                    "url": self._wiki_article_public_url(item.id),
                }
            )
        return rows

    def _wiki_search_rows(self, pages, term, path):
        """Liste de dicts {title, meta, snippet, url} pour le rapport QWeb."""
        rows = []
        path = path.split("?", 1)[0].rstrip("/") or "/wiki"
        for page in pages:
            plain = html2plaintext(self._wiki_visible_body_html(page) or "")
            rows.append(
                {
                    "title": page.name or "",
                    "meta": "Page",
                    "snippet": self._wiki_text_snippet(plain, term),
                    "url": f"{path}?page_id={page.id}",
                }
            )
        return rows

    def _wiki_layout_settings(self, page=None):
        """Réglages d'affichage : défauts site, surchargés par la page si définie."""
        website = self._wiki_current_website()
        if not website:
            show_toc = True
            show_page_nav = True
            border_color = "#000000"
        else:
            show_toc = bool(website.wiki_show_toc)
            show_page_nav = bool(website.wiki_show_page_nav)
            border_color = website.wiki_border_color or "#000000"

        if page:
            WikiPage = request.env["wiki.page"]
            show_toc = WikiPage._wiki_resolve_display_flag(page.show_toc, show_toc)
            show_page_nav = WikiPage._wiki_resolve_display_flag(
                page.show_page_nav, show_page_nav
            )

        return {
            "wiki_show_toc": show_toc,
            "wiki_border_color": border_color,
            "wiki_show_page_nav": show_page_nav,
        }

    def _wiki_toc_html(self, pages, current, base_path="/wiki"):
        # Liens toujours vers le portail wiki (pas vers l'URL de l'API / de la page courante).
        path = (base_path or "/wiki").split("?", 1)[0].rstrip("/") or "/wiki"
        cur_id = current.id if current else None
        pages_list = list(pages)

        def render_link(page, level=None):
            href = escape(f"{path}?page_id={page.id}")
            lvl = escape(str(level or page.level))
            name = escape(page.name or "")
            selected = " selected" if cur_id == page.id else ""
            return (
                f'<a class="o_wiki_toc_link o_wiki_toc_node level-{lvl}{selected}" '
                f'href="{href}" data-id="{page.id}" data-level="{lvl}">{name}</a>'
            )

        chunks = []
        i = 0
        while i < len(pages_list):
            page = pages_list[i]
            if page.level != "1":
                chunks.append(render_link(page))
                i += 1
                continue

            children = []
            j = i + 1
            while j < len(pages_list) and pages_list[j].level != "1":
                children.append(pages_list[j])
                j += 1

            if children:
                expanded = cur_id == page.id or any(c.id == cur_id for c in children)
                open_class = " is-open" if expanded else ""
                aria = "true" if expanded else "false"
                chunks.append(
                    f'<div class="o_wiki_toc_branch{open_class}" data-branch-id="{page.id}">'
                    f'<div class="o_wiki_toc_branch_head">'
                    f'<button type="button" class="o_wiki_toc_branch_toggle" '
                    f'aria-expanded="{aria}" aria-label="Développer ou réduire la section">'
                    f'<i class="fa fa-chevron-down" aria-hidden="true"></i>'
                    f"</button>"
                    f"{render_link(page)}"
                    f"</div>"
                    f'<div class="o_wiki_toc_children">'
                )
                for child in children:
                    chunks.append(render_link(child))
                chunks.append("</div></div>")
            else:
                chunks.append(render_link(page))

            i = j

        return Markup("".join(chunks))

    def _wiki_header_nav_items(self, pages, current, base_path="/wiki"):
        """Items de menu Header Wiki (niveau 1 + enfants) pour le rendu QWeb."""
        path = (base_path or "/wiki").split("?", 1)[0].rstrip("/") or "/wiki"
        cur_id = current.id if current else None
        pages_list = list(pages)
        items = []
        i = 0
        while i < len(pages_list):
            page = pages_list[i]
            if page.level != "1":
                i += 1
                continue
            children = []
            j = i + 1
            while j < len(pages_list) and pages_list[j].level != "1":
                children.append(pages_list[j])
                j += 1
            child_selected = cur_id is not None and any(c.id == cur_id for c in children)
            items.append(
                {
                    "page": page,
                    "children": children,
                    "url": f"{path}?page_id={page.id}",
                    "selected": cur_id == page.id or child_selected,
                }
            )
            i = j
        return items

    @http.route("/wiki", type="http", auth="public", website=True)
    def wiki_home(self, page_id=None, **kw):
        pages = request.env["wiki.page"].search(self._wiki_pages_domain(), order="sequence, id")
        raw_pid = page_id or kw.get("page_id") or request.params.get("page_id")
        try:
            page_id_int = int(raw_pid) if raw_pid else None
        except (TypeError, ValueError):
            page_id_int = None

        path = (request.httprequest.path or "/wiki").split("?", 1)[0]
        search_q = (kw.get("q") or request.params.get("q") or "").strip()
        raw_target = kw.get("wiki_item") or request.params.get("wiki_item") or kw.get("article_id") or request.params.get("article_id")
        if raw_target and not search_q:
            target = self._wiki_visible_article(raw_target)
            if target:
                return request.redirect(self._wiki_article_public_url(target.id))
        search_rows = []
        wiki_search_too_short = False
        if search_q:
            if len(search_q) < 2:
                wiki_search_too_short = True
            else:
                Wiki = request.env["wiki.page"]
                results = Wiki.search(
                    self._wiki_search_domain(search_q), order="sequence, id", limit=80
                )
                search_rows = self._wiki_search_rows(results, search_q, path)
                articles = (
                    request.env["wiki.gallery.item"]
                    .sudo()
                    .search(
                        self._wiki_articles_domain(search_q),
                        order="sequence, id desc",
                        limit=40,
                    )
                )
                search_rows.extend(self._wiki_article_rows(articles, search_q))

        wiki_article = False

        current = pages.filtered(lambda p: p.id == page_id_int)[:1] if page_id_int else False
        if not current and pages and not search_q and not wiki_article:
            current = pages[0]

        current_content = ""
        if current:
            if self._wiki_can_see_draft():
                current_content = current.content or ""
            elif current.state == "published":
                current_content = current.last_published_content or current.content or ""
            else:
                current_content = current.last_published_content or current.content or ""

        wiki_search_active = bool(search_q)
        # website.layout (utilisateurs internes) appelle main_object.fields_get() sans tester None.
        # En recherche wiki, main_object était None → AttributeError → HTTP 500.
        if current and current.has_page:
            main_object = current
        else:
            main_object = request.website

        values = {
            "pages": pages,
            "current": current,
            "current_content": current_content,
            "wiki_toc_html": self._wiki_toc_html(pages, current),
            "wiki_header_nav_items": self._wiki_header_nav_items(pages, current),
            "wiki_can_front_edit": self._wiki_can_front_edit(),
            "wiki_search_query": search_q,
            "wiki_search_rows": search_rows,
            "wiki_search_too_short": wiki_search_too_short,
            "wiki_search_active": wiki_search_active,
            "wiki_article": wiki_article,
            "main_object": main_object,
            # False : permet l'éditeur frontend du site (zone de titre / blocs).
            # Le contenu des pages wiki reste géré via le bouton « Editer » du portail.
            "edit_in_backend": False,
            **self._wiki_layout_settings(current),
        }
        return request.render("wiki_knowledge.wiki_portal_main", values)

    @http.route("/wiki/article/<int:article_id>", type="http", auth="public", website=True)
    def wiki_article(self, article_id, **kw):
        """Page de lecture d'un article de bibliothèque (photo pleine, HTML)."""
        item = self._wiki_visible_article(article_id)
        if not item:
            return request.not_found()
        view_count = item._register_view()
        pages = request.env["wiki.page"].search(self._wiki_pages_domain(), order="sequence, id")
        layout = self._wiki_layout_settings()
        layout["wiki_show_toc"] = False
        layout["wiki_show_page_nav"] = False
        values = {
            "pages": pages,
            "current": False,
            "current_content": "",
            "wiki_toc_html": self._wiki_toc_html(pages, False),
            "wiki_header_nav_items": self._wiki_header_nav_items(pages, False),
            "wiki_can_front_edit": False,
            "wiki_search_query": "",
            "wiki_search_rows": [],
            "wiki_search_too_short": False,
            "wiki_search_active": False,
            "wiki_article": {
                **self._wiki_article_payload(item),
                "view_count": view_count,
            },
            "main_object": request.website,
            "edit_in_backend": False,
            **layout,
        }
        return request.render("wiki_knowledge.wiki_portal_main", values)

    @http.route("/wiki/api/toc", type="json", auth="public", website=True, methods=["POST"])
    def wiki_api_toc(self, **kw):
        """Sommaire wiki pour le building block (isolé multi-site)."""
        pages = request.env["wiki.page"].search(self._wiki_pages_domain(), order="sequence, id")
        layout = self._wiki_layout_settings()
        return {
            "html": str(self._wiki_toc_html(pages, False, base_path="/wiki")),
            "border_color": layout["wiki_border_color"],
        }

    @http.route("/wiki/api/can_front_edit", type="json", auth="user", methods=["POST"])
    def wiki_api_can_front_edit(self, **kw):
        return {"can_edit": self._wiki_can_front_edit()}

    @http.route("/wiki/api/page/<int:page_id>/save", type="json", auth="user", methods=["POST"])
    def wiki_api_save_page(self, page_id, content=None, **kw):
        page = request.env["wiki.page"].browse(page_id)
        current_website = self._wiki_current_website()
        if not page.exists() or not page.has_page:
            return {"error": "not_editable"}
        if page.website_id and (not current_website or page.website_id != current_website):
            return {"error": "forbidden"}
        if not self._wiki_portal_company_allows_page(page):
            return {"error": "forbidden"}
        if not self._wiki_can_front_edit():
            return {"error": "forbidden"}
        if page.state == "to_review":
            return {"error": "locked_for_review"}
        vals = {"content": content or ""}
        if not page.website_id and current_website:
            vals["website_id"] = current_website.id
        page.write(vals)
        return {"ok": True}

