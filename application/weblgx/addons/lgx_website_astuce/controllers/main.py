# -*- coding: utf-8 -*-
from weblgx import http
from weblgx.http import request


class AstuceController(http.Controller):

    def _current_website(self):
        website = getattr(request, "website", False)
        if website:
            return website
        return request.env["website"].get_current_website()

    @http.route("/website/astuce/get", type="json", auth="public", website=True, methods=["POST"])
    def astuce_get(self, astuce_id=None, **kw):
        """Contenu public de l'astuce pour le building block (isolé multi-site)."""
        website = self._current_website()
        raw_id = astuce_id or kw.get("astuce_id")
        try:
            aid = int(raw_id) if raw_id else None
        except (TypeError, ValueError):
            aid = None
        return request.env["website.astuce"].get_public_payload(aid, website=website)

    @http.route("/website/astuce/list", type="json", auth="user", website=True, methods=["POST"])
    def astuce_list(self, **kw):
        """Liste des astuces du site courant (éditeur web)."""
        website = self._current_website()
        Astuce = request.env["website.astuce"]
        rows = Astuce.search_read(
            [("website_id", "=", website.id), ("active", "=", True)],
            ["id", "name"],
            order="sequence, id",
        )
        return {"astuces": rows, "website_id": website.id}
