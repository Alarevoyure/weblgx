# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse

from lxml import html as lxml_html

from weblgx import http
from weblgx.http import request
from weblgx.tools.misc import format_date

from weblgx.addons.wiki_knowledge.controllers.wiki_portal import WikiPortal

_DEFAULT_WIKI_IMAGE = "/wiki_knowledge/static/src/img/wiki_logo.png"
_IMG_SRC_RE = re.compile(
    r"""<img\b[^>]*?\bsrc\s*=\s*(?:["']([^"']+)["']|([^\s>]+))""",
    re.IGNORECASE | re.DOTALL,
)
# data:image trop court = souvent un pixel / placeholder inutile
_MIN_DATA_URL_LEN = 120


class WikiLatestArticlesController(http.Controller):

    def _current_website(self):
        website = getattr(request, "website", False)
        if website:
            return website
        return request.env["website"].get_current_website()

    def _is_usable_image_src(self, src):
        if not src:
            return False
        src = src.strip()
        if not src or src.startswith("#") or src.lower().startswith("javascript:"):
            return False
        lower = src.lower()
        if lower.startswith("data:"):
            if not lower.startswith("data:image/"):
                return False
            # SVG inline souvent décoratif / fragile en vignette
            if lower.startswith("data:image/svg"):
                return False
            return len(src) >= _MIN_DATA_URL_LEN
        if lower.startswith("/") or lower.startswith("http://") or lower.startswith("https://"):
            path = urlparse(src).path.lower() if "://" in lower else lower.split("?", 1)[0]
            banned = (
                "/web/static/img/placeholder",
                "favicon",
            )
            if any(b in path for b in banned):
                return False
            return True
        return False

    def _extract_first_image(self, html_content):
        """Première image exploitable du corps HTML, ou None."""
        if not html_content or not isinstance(html_content, str):
            return None
        try:
            root = lxml_html.fromstring(html_content)
            for img in root.xpath("//img[@src]"):
                src = (img.get("src") or "").strip()
                if self._is_usable_image_src(src):
                    return src
        except Exception:
            pass
        for match in _IMG_SRC_RE.finditer(html_content):
            src = (match.group(1) or match.group(2) or "").strip()
            if self._is_usable_image_src(src):
                return src
        return None

    @http.route(
        "/wiki/api/latest_articles",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def latest_articles(self, limit=5, default_image=None, **kw):
        try:
            limit = int(limit or 5)
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 20))

        fallback = (default_image or "").strip() or _DEFAULT_WIKI_IMAGE
        if not (
            self._is_usable_image_src(fallback)
            or fallback.startswith("/wiki_knowledge/")
        ):
            fallback = _DEFAULT_WIKI_IMAGE

        portal = WikiPortal()
        lang = request.env.lang or "fr_FR"
        # Périmètre strict multi-site : pages et articles de bibliothèque du site courant.
        # On prend `limit` de chaque source, puis les plus récents au global.
        domain = portal._wiki_pages_domain() + [("has_page", "=", True)]
        pages = (
            request.env["wiki.page"]
            .sudo()
            .search(domain, order="write_date desc, id desc", limit=limit)
        )
        articles = (
            request.env["wiki.gallery.item"]
            .sudo()
            .search(
                portal._wiki_articles_domain(),
                order="write_date desc, id desc",
                limit=limit,
            )
        )
        entries = []
        for page in pages:
            body = portal._wiki_visible_body_html(page)
            entries.append(
                {
                    "sort": page.write_date or page.create_date,
                    "id": "page-%s" % page.id,
                    "name": page.name or "",
                    "url": f"/wiki?page_id={page.id}",
                    "image_url": self._extract_first_image(body) or fallback,
                    "date_label": self._added_label(page.create_date, lang),
                    "meta": "",
                }
            )
        for item in articles:
            gallery_name = (item.gallery_id.name or "").strip()
            url = portal._wiki_article_public_url(item.id)
            added = item.submitted_date or item.create_date
            entries.append(
                {
                    "sort": item.write_date or added,
                    "id": "article-%s" % item.id,
                    "name": (item.name or "").strip() or "Sans titre",
                    "url": url,
                    "image_url": f"/web/image/wiki.gallery.item/{item.id}/image",
                    "date_label": self._added_label(added, lang),
                    "meta": gallery_name,
                }
            )

        entries.sort(key=lambda entry: (entry["sort"] is not None, entry["sort"] or ""), reverse=True)
        items = []
        for entry in entries[:limit]:
            entry.pop("sort", None)
            items.append(entry)
        website = self._current_website()
        return {"items": items, "website_id": website.id if website else False}

    def _added_label(self, date_value, lang):
        if not date_value:
            return ""
        try:
            date_str = format_date(
                request.env,
                date_value,
                lang_code=lang,
                date_format="d MMMM y",
            )
        except Exception:
            date_str = format_date(request.env, date_value, lang_code=lang)
        return ("Ajouté le %s" % date_str) if date_str else ""
