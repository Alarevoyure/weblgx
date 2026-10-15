# -*- coding: utf-8 -*-
from weblgx import http
from weblgx.http import request

from weblgx.addons.wiki_knowledge.controllers.wiki_portal import WikiPortal


class WikiPopularArticlesController(http.Controller):

    def _current_website(self):
        website = getattr(request, "website", False)
        if website:
            return website
        return request.env["website"].get_current_website()

    @http.route(
        "/wiki/api/popular_articles",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def popular_articles(self, limit=4, **kw):
        """Articles de bibliothèque du site courant, les plus ouverts d'abord."""
        try:
            limit = int(limit or 4)
        except (TypeError, ValueError):
            limit = 4
        limit = max(2, min(limit, 6))

        portal = WikiPortal()
        articles = (
            request.env["wiki.gallery.item"]
            .sudo()
            .search(
                portal._wiki_articles_domain(),
                order="view_count desc, submitted_date desc, id desc",
                limit=limit,
            )
        )
        items = []
        for item in articles:
            items.append(
                {
                    "id": item.id,
                    "name": (item.name or "").strip() or "Sans titre",
                    "url": portal._wiki_article_public_url(item.id),
                    "image_url": "/web/image/wiki.gallery.item/%s/image" % item.id,
                    "view_count": int(item.view_count or 0),
                }
            )
        website = self._current_website()
        return {"items": items, "website_id": website.id if website else False}
