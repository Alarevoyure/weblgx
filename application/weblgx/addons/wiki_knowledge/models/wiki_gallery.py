# -*- coding: utf-8 -*-
from weblgx import api, fields, models


class WikiGallery(models.Model):
    _name = "wiki.gallery"
    _description = "Bibliothèque d'images Wiki"
    _order = "name, id"

    name = fields.Char(
        string="Nom",
        required=True,
        help="Ex. : nom de la page ou du sujet (une bibliothèque par page).",
    )
    active = fields.Boolean(default=True)
    website_id = fields.Many2one(
        "website",
        string="Site web",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: self.env["website"].get_current_website(),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="website_id.company_id",
        store=True,
        readonly=True,
    )
    description = fields.Text(string="Description")
    item_ids = fields.One2many(
        "wiki.gallery.item",
        "gallery_id",
        string="Contributions",
    )
    item_count = fields.Integer(
        string="Nb contributions",
        compute="_compute_item_count",
    )
    pending_count = fields.Integer(
        string="À valider",
        compute="_compute_item_count",
    )

    @api.depends("item_ids", "item_ids.state")
    def _compute_item_count(self):
        for gallery in self:
            items = gallery.item_ids
            gallery.item_count = len(items)
            gallery.pending_count = len(items.filtered(lambda i: i.state == "submitted"))

    def action_open_items(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.name,
            "res_model": "wiki.gallery.item",
            "view_mode": "kanban,tree,form",
            "domain": [("gallery_id", "=", self.id)],
            "context": {
                "default_gallery_id": self.id,
                "default_website_id": self.website_id.id,
                "search_default_to_validate": 1,
            },
        }

    @api.model
    def _migrate_orphan_items(self):
        """Rattache les anciennes contributions sans bibliothèque."""
        Item = self.env["wiki.gallery.item"].sudo()
        orphans = Item.search([("gallery_id", "=", False)])
        if not orphans:
            return
        Website = self.env["website"].sudo()
        # website_id peut être vide (related) : rattacher au 1er site ou via contexte.
        for orphan in orphans:
            website = orphan.website_id
            if not website:
                website = Website.get_current_website() or Website.search([], limit=1)
            if not website:
                continue
            gallery = self.sudo().search(
                [
                    ("website_id", "=", website.id),
                    ("name", "=", "Bibliothèque générale"),
                ],
                limit=1,
            )
            if not gallery:
                gallery = self.sudo().create(
                    {
                        "name": "Bibliothèque générale",
                        "website_id": website.id,
                    }
                )
            orphan.write({"gallery_id": gallery.id})

    def action_purge_with_items(self):
        """Supprime la bibliothèque et toutes ses contributions."""
        for gallery in self:
            gallery.item_ids.unlink()
        return self.unlink()

    def _register_hook(self):
        super()._register_hook()
        self._migrate_orphan_items()
