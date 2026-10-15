# -*- coding: utf-8 -*-
import logging
import re

from weblgx import _, api, fields, models, tools
from weblgx.exceptions import UserError
from weblgx.tools.misc import html_escape

_logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(
    r"<(p|div|br|/p|ul|ol|li|h[1-6]|strong|em|b|i|a|span|blockquote)\b",
    re.IGNORECASE,
)
_BRAND = "#16213e"
_BRAND_SOFT = "#eef1f6"


class WikiGalleryItem(models.Model):
    _name = "wiki.gallery.item"
    _description = "Contribution bibliothèque Wiki"
    _order = "sequence, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Titre",
        required=True,
        tracking=True,
        help="Titre de l'article, affiché sur la tuile et dans l'article complet.",
    )
    text = fields.Html(
        string="Texte",
        required=True,
        sanitize=True,
        sanitize_attributes=True,
        strip_style=True,
        tracking=True,
    )
    text_preview = fields.Text(
        string="Aperçu texte",
        compute="_compute_text_preview",
    )
    image = fields.Image(
        string="Photo",
        required=True,
        max_width=1920,
        max_height=1920,
    )
    media = fields.Binary(
        string="Vidéo ou audio",
        attachment=True,
        help="Fichier facultatif : MP4 (50 Mo) ou MP3 / M4A (20 Mo).",
    )
    media_filename = fields.Char(string="Nom du fichier média")
    media_mimetype = fields.Char(string="Type du média")
    contributor_name = fields.Char(
        string="Nom du contributeur",
        tracking=True,
    )
    contributor_email = fields.Char(
        string="Email du contributeur",
        required=True,
        tracking=True,
        help="Adresse e-mail obligatoire pour le dépôt (visible uniquement en validation).",
    )
    gallery_id = fields.Many2one(
        "wiki.gallery",
        string="Bibliothèque",
        required=False,
        ondelete="cascade",
        index=True,
        tracking=True,
        help="Bibliothèque / page à laquelle rattacher cette contribution.",
    )
    website_id = fields.Many2one(
        "website",
        string="Site web",
        related="gallery_id.website_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="gallery_id.company_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("submitted", "À valider"),
            ("published", "Publié"),
            ("refused", "Refusé"),
        ],
        string="Statut",
        default="submitted",
        required=True,
        tracking=True,
        index=True,
    )
    sequence = fields.Integer(default=10)
    view_count = fields.Integer(
        string="Vues",
        default=0,
        readonly=True,
        copy=False,
        index=True,
        help="Nombre d'ouvertures de la page article. Chaque ouverture compte, "
        "y compris plusieurs fois par le même visiteur.",
    )
    submitted_date = fields.Datetime(
        string="Date de dépôt",
        default=fields.Datetime.now,
        readonly=True,
    )

    @api.depends("text")
    def _compute_text_preview(self):
        for rec in self:
            plain = tools.html2plaintext(rec.text or "").strip()
            rec.text_preview = plain[:400] if plain else ""

    @api.model
    def _sanitize_contribution_html(self, raw):
        """Nettoie le HTML public (dépôt visiteur / validation)."""
        return tools.html_sanitize(
            raw or "",
            sanitize_attributes=True,
            strip_style=True,
            strip_classes=True,
        )

    def _text_as_html(self):
        """HTML prêt à afficher (convertit l'ancien texte brut si besoin)."""
        self.ensure_one()
        raw = self.text or ""
        if not raw:
            return ""
        if _HTML_TAG_RE.search(raw):
            return self._sanitize_contribution_html(raw)
        escaped = tools.html_escape(raw).replace("\n", "<br/>\n")
        return f"<p>{escaped}</p>"

    def _plain_text(self):
        self.ensure_one()
        return tools.html2plaintext(self.text or "").strip()

    def _summary(self, max_len=180):
        """Résumé tronqué pour les tuiles (ellipse si plus long)."""
        self.ensure_one()
        plain = re.sub(r"\s+", " ", self._plain_text()).strip()
        if not plain:
            return ""
        if len(plain) <= max_len:
            return plain
        cut = plain[: max_len + 1]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        else:
            cut = plain[:max_len]
        return cut.rstrip(".,;: ") + "..."

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "text" in vals and vals["text"]:
                vals["text"] = self._sanitize_contribution_html(vals["text"])
            if "name" in vals and vals["name"]:
                vals["name"] = (vals["name"] or "").strip()[:120]
        records = super().create(vals_list)
        records._sync_media_attachment()
        records.filtered(lambda rec: rec.state == "submitted")._notify_reviewer_submission()
        return records

    def write(self, vals):
        vals = dict(vals)
        # Le compteur passe par SQL (_register_view), jamais par un formulaire.
        vals.pop("view_count", None)
        if "text" in vals and vals["text"]:
            vals["text"] = self._sanitize_contribution_html(vals["text"])
        if "name" in vals and vals["name"]:
            vals["name"] = (vals["name"] or "").strip()[:120]
        result = super().write(vals)
        if any(key in vals for key in ("media", "media_filename", "media_mimetype")):
            self._sync_media_attachment()
        return result

    def _register_view(self):
        """Compte une ouverture de la page article. Une requête HTTP = une vue."""
        self.ensure_one()
        self.env.cr.execute(
            """
            UPDATE wiki_gallery_item
               SET view_count = COALESCE(view_count, 0) + 1
             WHERE id = %s
            RETURNING view_count
            """,
            (self.id,),
        )
        row = self.env.cr.fetchone()
        self.invalidate_recordset(["view_count"])
        return int(row[0]) if row else 0

    def _media_kind(self):
        """'video', 'audio', ou chaîne vide. Ne charge pas le fichier."""
        self.ensure_one()
        mime = (self.media_mimetype or "").lower()
        if mime.startswith("video/"):
            return "video"
        if mime.startswith("audio/"):
            return "audio"
        return ""

    def _sync_media_attachment(self):
        """Le lecteur a besoin du vrai type (MP4 / MP3), pas d'un octet-stream."""
        Attachment = self.env["ir.attachment"].sudo()
        for rec in self:
            attachment = Attachment.search(
                [
                    ("res_model", "=", rec._name),
                    ("res_field", "=", "media"),
                    ("res_id", "=", rec.id),
                ],
                limit=1,
            )
            if not attachment or not rec.media_mimetype:
                continue
            attachment.write(
                {
                    "name": rec.media_filename or "media",
                    "mimetype": rec.media_mimetype,
                }
            )

    def _wiki_is_reviewer(self):
        u = self.env.user
        return (
            u.has_group("wiki_knowledge.group_wiki_reviewer")
            or u.has_group("wiki_knowledge.group_wiki_manager")
            or u.has_group("base.group_system")
        )

    def action_publish(self):
        if not self._wiki_is_reviewer():
            raise UserError(_("Seuls les valideurs Wiki peuvent publier une contribution."))
        for rec in self:
            if not (rec.name or "").strip():
                raise UserError(_("Le titre est obligatoire pour publier."))
            if not rec.image or not rec._plain_text():
                raise UserError(_("Photo et texte sont obligatoires pour publier."))
        targets = self.filtered(lambda r: r.state != "published")
        self.write({"state": "published"})
        return targets._notify_contributor_decision("published")

    def action_refuse(self):
        if not self._wiki_is_reviewer():
            raise UserError(_("Seuls les valideurs Wiki peuvent refuser une contribution."))
        targets = self.filtered(lambda r: r.state != "refused")
        self.write({"state": "refused"})
        return targets._notify_contributor_decision("refused")

    def action_reset_to_submitted(self):
        if not self._wiki_is_reviewer():
            raise UserError(_("Seuls les valideurs Wiki peuvent rouvrir une contribution."))
        self.write({"state": "submitted"})

    def _decision_company(self):
        self.ensure_one()
        return (
            self.company_id
            or (self.website_id.company_id if self.website_id else False)
            or self.env.company
        )

    def _decision_email_from(self, company, mail_server=None):
        self.ensure_one()
        company = company.sudo()
        email_from = (
            (company.partner_id.email_formatted if company.partner_id else False)
            or company.email
            or company.default_from_email
        )
        if email_from:
            return email_from
        server = mail_server or self.env["ir.mail_server"].sudo()._mail_servers_for_company(
            company
        )[:1]
        if server and server.smtp_user and "@" in (server.smtp_user or ""):
            return server.smtp_user
        return False

    def _decision_email_body(self, decision):
        """HTML soigné (Midnight) pour validation / refus."""
        self.ensure_one()
        greeting_name = (self.contributor_name or "").strip()
        hello = (
            _("Bonjour %s,") % html_escape(greeting_name)
            if greeting_name
            else _("Bonjour,")
        )
        title = html_escape((self.name or "").strip() or _("Sans titre"))
        gallery = html_escape(self.gallery_id.name or _("Bibliothèque Wiki"))
        site = html_escape(
            (self.website_id.name if self.website_id else "")
            or (self.company_id.name if self.company_id else "")
            or ""
        )
        if decision == "published":
            badge = _("Publié")
            badge_bg = "#1b7f4e"
            headline = _("Merci pour votre participation !")
            lead = _(
                "Bonne nouvelle : votre article <strong>%(title)s</strong> "
                "a été validé et est désormais visible dans "
                "<strong>%(gallery)s</strong>."
            ) % {"title": title, "gallery": gallery}
            thanks = _(
                "Un grand merci pour votre contribution : elle enrichit "
                "la mémoire collective et inspire les autres visiteurs."
            )
            footer_note = _(
                "Vous pouvez retrouver votre article sur le site, "
                "dans la bibliothèque correspondante."
            )
        else:
            badge = _("Non publié")
            badge_bg = "#a33b3b"
            headline = _("Suite donnée à votre contribution")
            lead = _(
                "Après relecture, votre article <strong>%(title)s</strong> "
                "proposé pour <strong>%(gallery)s</strong> "
                "n'a pas pu être publié."
            ) % {"title": title, "gallery": gallery}
            thanks = _(
                "Nous vous remercions sincèrement d'avoir pris le temps "
                "de partager votre texte et votre photo. "
                "N'hésitez pas à proposer une nouvelle contribution."
            )
            footer_note = _(
                "Si vous avez des questions, contactez l'équipe du site."
            )

        site_line = (
            f'<p style="margin:0 0 8px;font-size:13px;color:#6b7280;">{site}</p>'
            if site
            else ""
        )
        return f"""
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:{_BRAND_SOFT};padding:24px 12px;font-family:Georgia,'Times New Roman',serif;">
  <tr>
    <td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" width="560" style="max-width:560px;width:100%;background:#ffffff;border-collapse:collapse;">
        <tr>
          <td style="background:{_BRAND};color:#ffffff;padding:28px 32px;">
            <p style="margin:0 0 6px;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.85;font-family:Arial,Helvetica,sans-serif;">Wiki</p>
            <h1 style="margin:0;font-size:26px;line-height:1.25;font-weight:700;">{html_escape(gallery)}</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 32px 8px;">
            <span style="display:inline-block;background:{badge_bg};color:#fff;font-family:Arial,Helvetica,sans-serif;font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;padding:6px 12px;border-radius:2px;">{html_escape(badge)}</span>
          </td>
        </tr>
        <tr>
          <td style="padding:8px 32px 28px;color:{_BRAND};">
            <p style="margin:0 0 16px;font-size:17px;line-height:1.5;font-family:Arial,Helvetica,sans-serif;">{hello}</p>
            <h2 style="margin:0 0 14px;font-size:22px;line-height:1.3;">{html_escape(headline)}</h2>
            <p style="margin:0 0 16px;font-size:16px;line-height:1.6;font-family:Arial,Helvetica,sans-serif;color:#243047;">{lead}</p>
            <p style="margin:0 0 16px;font-size:16px;line-height:1.6;font-family:Arial,Helvetica,sans-serif;color:#243047;">{thanks}</p>
            <p style="margin:0;font-size:14px;line-height:1.55;font-family:Arial,Helvetica,sans-serif;color:#5b6578;">{footer_note}</p>
          </td>
        </tr>
        <tr>
          <td style="border-top:1px solid #e5e8ef;padding:18px 32px 24px;background:#fbfcfe;">
            {site_line}
            <p style="margin:0;font-size:12px;line-height:1.5;color:#8a93a6;font-family:Arial,Helvetica,sans-serif;">
              {html_escape(_("Cet email a été envoyé automatiquement suite à la relecture de votre contribution."))}
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
""".strip()

    def _notify_contributor_decision(self, decision):
        """Envoie l'email de décision ; n'empêche pas la validation en cas d'échec SMTP."""
        if decision not in ("published", "refused"):
            return False
        sent = 0
        failed = 0
        skipped = 0
        for rec in self:
            email_to = (rec.contributor_email or "").strip()
            if not email_to:
                skipped += 1
                continue
            company = rec._decision_company()
            mail_server = (
                self.env["ir.mail_server"].sudo()._mail_servers_for_company(company)[:1]
            )
            email_from = rec._decision_email_from(company, mail_server=mail_server)
            if not email_from:
                failed += 1
                _logger.warning(
                    "Pas d'expéditeur pour notifier le contributeur "
                    "(item %s, company %s)",
                    rec.id,
                    company.id if company else None,
                )
                continue

            title = (rec.name or "").strip() or _("Sans titre")
            if decision == "published":
                subject = _("Wiki — Votre article « %s » est publié") % title
            else:
                subject = _("Wiki — Suite donnée à votre article « %s »") % title

            mail_vals = {
                "subject": subject,
                "email_from": email_from,
                "email_to": email_to,
                "body_html": rec._decision_email_body(decision),
                "auto_delete": True,
            }
            if mail_server:
                mail_vals["mail_server_id"] = mail_server.id
            try:
                mail = (
                    self.env["mail.mail"]
                    .sudo()
                    .with_company(company)
                    .create(mail_vals)
                )
                mail.send(raise_exception=True)
                sent += 1
                _logger.info(
                    "Email décision Wiki gallery (%s) envoyé à %s (item %s)",
                    decision,
                    email_to,
                    rec.id,
                )
            except Exception:
                failed += 1
                _logger.exception(
                    "Échec email décision Wiki gallery (%s) à %s (item %s)",
                    decision,
                    email_to,
                    rec.id,
                )

        if decision == "published":
            title = _("Article publié")
            if sent and not failed:
                message = _("Un email de remerciement a été envoyé au contributeur.")
                ntype = "success"
            elif sent and failed:
                message = _(
                    "Article publié. Certains emails n'ont pas pu être envoyés."
                )
                ntype = "warning"
            elif failed:
                message = _(
                    "Article publié, mais l'email au contributeur n'a pas pu être envoyé."
                )
                ntype = "warning"
            else:
                message = _("Article publié.")
                ntype = "success"
        else:
            title = _("Article refusé")
            if sent and not failed:
                message = _("Un email d'information a été envoyé au contributeur.")
                ntype = "success"
            elif failed:
                message = _(
                    "Article refusé, mais l'email au contributeur n'a pas pu être envoyé."
                )
                ntype = "warning"
            else:
                message = _("Article refusé.")
                ntype = "success"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": ntype,
                "sticky": False,
                # Sans cette action, la notification remplace le rechargement
                # de la fiche : le statut reste visuellement sur « À valider ».
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _notify_reviewer_submission(self):
        """Prévient l'adresse du site. Un échec d'envoi ne bloque pas le dépôt."""
        for rec in self:
            try:
                rec._notify_reviewer_submission_one()
            except Exception:
                _logger.exception(
                    "Échec de l'email de validation Wiki (item %s)",
                    rec.id,
                )

    def _notify_reviewer_submission_one(self):
        self.ensure_one()
        website = self.website_id
        email_to = ((website.wiki_review_email or "").strip() if website else "")
        if not email_to or "@" not in email_to:
            return

        company = self._decision_company()
        mail_server = self.env["ir.mail_server"].sudo()._mail_servers_for_company(company)[:1]
        email_from = self._decision_email_from(company, mail_server=mail_server)
        if not email_from:
            _logger.warning(
                "Pas d'expéditeur pour l'email de validation Wiki (item %s, company %s)",
                self.id,
                company.id if company else None,
            )
            return

        title = (self.name or "").strip() or _("Sans titre")
        gallery = html_escape(self.gallery_id.name or _("Bibliothèque Wiki"))
        site = html_escape((website.name if website else "") or "")
        contributor = html_escape((self.contributor_name or "").strip())
        contributor_email = html_escape((self.contributor_email or "").strip())
        who = contributor
        if contributor and contributor_email:
            who = f"{contributor} ({contributor_email})"
        elif contributor_email:
            who = contributor_email
        summary = html_escape(self._summary(240))
        base = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url") or ""
        ).rstrip("/")
        link = (
            f"{base}/web#id={self.id}&amp;model=wiki.gallery.item&amp;view_type=form"
            if base
            else ""
        )
        link_html = (
            f'<p style="margin:20px 0 0;">'
            f'<a href="{link}" style="display:inline-block;background:{_BRAND};color:#ffffff;'
            f'font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:700;'
            f'text-decoration:none;padding:10px 16px;">Ouvrir la contribution</a></p>'
            if link
            else ""
        )
        who_html = (
            f'<p style="margin:0 0 12px;font-size:15px;line-height:1.55;'
            f'font-family:Arial,Helvetica,sans-serif;color:#243047;">'
            f"Déposé par {who}.</p>"
            if who
            else ""
        )
        summary_html = (
            f'<p style="margin:0;font-size:15px;line-height:1.55;'
            f'font-family:Arial,Helvetica,sans-serif;color:#5b6578;">{summary}</p>'
            if summary
            else ""
        )
        site_line = (
            f'<p style="margin:0 0 8px;font-size:13px;color:#6b7280;">{site}</p>'
            if site
            else ""
        )
        body = f"""
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:{_BRAND_SOFT};padding:24px 12px;font-family:Georgia,'Times New Roman',serif;">
  <tr>
    <td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" width="560" style="max-width:560px;width:100%;background:#ffffff;border-collapse:collapse;">
        <tr>
          <td style="background:{_BRAND};color:#ffffff;padding:28px 32px;">
            <p style="margin:0 0 6px;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.85;font-family:Arial,Helvetica,sans-serif;">Wiki</p>
            <h1 style="margin:0;font-size:24px;line-height:1.25;font-weight:700;">Article à valider</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 32px;color:{_BRAND};">
            <p style="margin:0 0 14px;font-size:16px;line-height:1.6;font-family:Arial,Helvetica,sans-serif;color:#243047;">
              Un article est arrivé dans <strong>{gallery}</strong>.
            </p>
            <h2 style="margin:0 0 14px;font-size:22px;line-height:1.3;">{html_escape(title)}</h2>
            {who_html}
            {summary_html}
            {link_html}
          </td>
        </tr>
        <tr>
          <td style="border-top:1px solid #e5e8ef;padding:18px 32px 24px;background:#fbfcfe;">
            {site_line}
            <p style="margin:0;font-size:12px;line-height:1.5;color:#8a93a6;font-family:Arial,Helvetica,sans-serif;">
              Cet email a été envoyé automatiquement à l'adresse de validation des articles.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
""".strip()
        mail_vals = {
            "subject": _("Wiki — Article à valider : %s") % title,
            "email_from": email_from,
            "email_to": email_to,
            "body_html": body,
            "auto_delete": True,
        }
        if mail_server:
            mail_vals["mail_server_id"] = mail_server.id
        mail = self.env["mail.mail"].sudo().with_company(company).create(mail_vals)
        mail.send(raise_exception=True)
        _logger.info(
            "Email de validation Wiki envoyé à %s (item %s, site %s)",
            email_to,
            self.id,
            website.id if website else None,
        )

    @api.model
    def get_published_payload(self, gallery_id=None, website=None):
        """Liste publique des contributions publiées (filtrée par bibliothèque)."""
        website = website or self.env["website"].get_current_website()
        domain = [
            ("website_id", "=", website.id),
            ("state", "=", "published"),
        ]
        if gallery_id:
            domain.append(("gallery_id", "=", int(gallery_id)))
        else:
            # Sans bibliothèque sélectionnée : ne rien exposer (évite le mélange entre pages).
            return {"items": [], "gallery_id": False}
        items = self.sudo().search(domain, order="sequence, id")
        rows = []
        for item in items:
            rows.append(
                {
                    "id": item.id,
                    "name": (item.name or "").strip() or _("Sans titre"),
                    "gallery_name": item.gallery_id.name or "",
                    "summary": item._summary(),
                    "text": item._text_as_html(),
                    "contributor_name": item.contributor_name or "",
                    "image_url": f"/web/image/wiki.gallery.item/{item.id}/image",
                    "media_kind": item._media_kind(),
                }
            )
        return {"items": rows, "gallery_id": int(gallery_id)}
