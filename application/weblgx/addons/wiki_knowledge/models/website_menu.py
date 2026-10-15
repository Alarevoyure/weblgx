from weblgx import api, models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    @api.model
    def _weblgx_ensure_default_wiki_menu(self):
        """Remplace l'entrée Blog par Wiki sur le site par défaut et le menu modèle."""
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if website and website.menu_id:
            self._weblgx_blog_menu_to_wiki_parent(website.menu_id, website.id)
        template = self.env.ref("website.main_menu", raise_if_not_found=False)
        self._weblgx_blog_menu_to_wiki_parent(template, False)

    @api.model
    def _weblgx_blog_menu_to_wiki_parent(self, parent, website_id):
        if not parent:
            return
        Menu = self.sudo()
        children = Menu.search([("parent_id", "=", parent.id)])
        blog = children.filtered(lambda menu: (menu.url or "").rstrip("/") == "/blog")
        wiki = children.filtered(lambda menu: (menu.url or "").rstrip("/") == "/wiki")
        if blog and not wiki:
            self._weblgx_rename_menu_wiki(blog[:1])
            if len(blog) > 1:
                blog[1:].unlink()
            return
        if blog and wiki:
            blog.unlink()
            return
        if wiki:
            return
        Menu.create({
            "name": "Wiki",
            "url": "/wiki",
            "parent_id": parent.id,
            "website_id": website_id,
            "sequence": 40,
        })

    @api.model
    def _weblgx_rename_menu_wiki(self, menu):
        menu.sudo().write({"url": "/wiki"})
        for code, _label in self.env["res.lang"].get_installed():
            menu.with_context(lang=code).sudo().write({"name": "Wiki"})
