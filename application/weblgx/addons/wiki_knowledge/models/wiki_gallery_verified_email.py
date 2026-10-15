# -*- coding: utf-8 -*-
from weblgx import api, fields, models


class WikiGalleryVerifiedEmail(models.Model):
    _name = "wiki.gallery.verified.email"
    _description = "Email déjà confirmé sur un site Wiki"
    _order = "id desc"

    email = fields.Char(required=True, index=True)
    website_id = fields.Many2one(
        "website",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="website_id.company_id",
        store=True,
        index=True,
    )

    _sql_constraints = [
        (
            "email_website_uniq",
            "unique(email, website_id)",
            "Cette adresse est déjà confirmée pour ce site.",
        ),
    ]

    @api.model
    def _normalize(self, email):
        return (email or "").strip().lower()

    @api.model
    def is_verified(self, email, website):
        """Vrai si cette adresse a déjà saisi un code valide sur ce site."""
        email = self._normalize(email)
        if not email or not website:
            return False
        return bool(
            self.sudo().search_count(
                [
                    ("email", "=", email),
                    ("website_id", "=", website.id),
                ]
            )
        )

    @api.model
    def remember(self, email, website):
        """Mémorise l'adresse après un code accepté. Isolé par site."""
        email = self._normalize(email)
        if not email or not website:
            return self.browse()
        existing = self.sudo().search(
            [
                ("email", "=", email),
                ("website_id", "=", website.id),
            ],
            limit=1,
        )
        if existing:
            return existing
        return self.sudo().create(
            {
                "email": email,
                "website_id": website.id,
            }
        )
