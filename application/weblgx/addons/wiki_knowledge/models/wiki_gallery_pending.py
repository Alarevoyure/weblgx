# -*- coding: utf-8 -*-
import logging
import secrets
from datetime import timedelta

from weblgx import _, api, fields, models
from weblgx.exceptions import UserError
from weblgx.tools.misc import html_escape

_logger = logging.getLogger(__name__)

_CODE_TTL_MINUTES = 20
_MAX_ATTEMPTS = 5


class WikiGalleryPending(models.Model):
    _name = "wiki.gallery.pending"
    _description = "Dépôt bibliothèque Wiki en attente de confirmation email"
    _order = "id desc"

    token = fields.Char(required=True, index=True, copy=False)
    code = fields.Char(required=True, copy=False)
    name = fields.Char(string="Titre", required=True)
    text = fields.Html(string="Texte", required=True, sanitize=True)
    image = fields.Binary(string="Photo", required=True, attachment=False)
    media = fields.Binary(string="Vidéo ou audio", attachment=True)
    media_filename = fields.Char(string="Nom du fichier média")
    media_mimetype = fields.Char(string="Type du média")
    contributor_name = fields.Char(string="Nom du contributeur")
    contributor_email = fields.Char(string="Email", required=True)
    gallery_id = fields.Many2one(
        "wiki.gallery",
        string="Bibliothèque",
        required=True,
        ondelete="cascade",
        index=True,
    )
    website_id = fields.Many2one(
        "website",
        string="Site web",
        related="gallery_id.website_id",
        store=True,
        index=True,
    )
    attempts = fields.Integer(default=0)
    expire_date = fields.Datetime(required=True, index=True)

    _sql_constraints = [
        ("token_uniq", "unique(token)", "Le jeton de confirmation doit être unique."),
    ]

    @api.model
    def _generate_code(self):
        return f"{secrets.randbelow(1_000_000):06d}"

    @api.model
    def _generate_token(self):
        return secrets.token_urlsafe(24)

    @api.model
    def create_pending(self, vals):
        """Crée un dépôt temporaire + envoie le code par email."""
        now = fields.Datetime.now()
        code = self._generate_code()
        token = self._generate_token()
        pending = self.sudo().create(
            {
                **vals,
                "token": token,
                "code": code,
                "attempts": 0,
                "expire_date": now + timedelta(minutes=_CODE_TTL_MINUTES),
            }
        )
        try:
            pending._send_verification_email()
        except Exception:
            pending.unlink()
            raise
        self._purge_expired()
        return pending

    def _resolve_mail_server(self, company):
        """SMTP de la société du site, sinon société ID=1."""
        self.ensure_one()
        return self.env["ir.mail_server"].sudo()._mail_servers_for_company(company)[:1]

    def _resolve_email_from(self, company, mail_server=None):
        """From du site courant (alias domaine), jamais la société « globale » du process."""
        self.ensure_one()
        company = company.sudo()
        email_from = (
            (company.partner_id.email_formatted if company.partner_id else False)
            or company.email
            or company.default_from_email
        )
        if email_from:
            return email_from
        # Dernier recours : compte SMTP de la société (ou repli société 1).
        server = mail_server or self._resolve_mail_server(company)
        if server and server.smtp_user and "@" in (server.smtp_user or ""):
            return server.smtp_user
        return False

    def _send_verification_email(self):
        """Envoi SMTP immédiat via mail.mail (raise_exception), From = société du site."""
        self.ensure_one()
        email_to = (self.contributor_email or "").strip()
        if not email_to:
            raise UserError(_("L'email est obligatoire pour envoyer le code."))

        company = (
            self.website_id.company_id
            if self.website_id and self.website_id.company_id
            else self.env.company
        )
        mail_server = self._resolve_mail_server(company)
        email_from = self._resolve_email_from(company, mail_server=mail_server)
        if not email_from:
            raise UserError(
                _(
                    "Aucune adresse d'expédition configurée pour ce site. "
                    "Renseignez l'email de la société ou le domaine d'alias."
                )
            )

        title = html_escape(self.name or "")
        code = html_escape(self.code or "")
        body = _(
            "<p>Bonjour,</p>"
            "<p>Vous avez proposé l'article <strong>%(title)s</strong> "
            "dans la bibliothèque Wiki.</p>"
            "<p>Votre code de confirmation est :</p>"
            "<p style=\"font-size:28px;font-weight:700;letter-spacing:4px;\">%(code)s</p>"
            "<p>Ce code est valable %(minutes)s minutes.</p>"
            "<p>Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>"
        ) % {
            "title": title,
            "code": code,
            "minutes": _CODE_TTL_MINUTES,
        }
        subject = _("Wiki — Code de confirmation : %s") % (self.code or "")

        # with_company : default_from / bounce du bon domaine (multi-site SaaS).
        Mail = self.env["mail.mail"].sudo().with_company(company)
        mail_vals = {
            "subject": subject,
            "email_from": email_from,
            "email_to": email_to,
            "body_html": body,
            "auto_delete": True,
        }
        if mail_server:
            mail_vals["mail_server_id"] = mail_server.id
        mail = Mail.create(mail_vals)
        try:
            # raise_exception=True : envoi SMTP synchrone, pas de file / cron silencieux.
            mail.send(raise_exception=True)
        except Exception:
            _logger.exception(
                "Échec d'envoi immédiat du code Wiki gallery à %s "
                "(pending %s, from=%s, company=%s)",
                email_to,
                self.id,
                email_from,
                company.id,
            )
            try:
                if mail.exists():
                    mail.unlink()
            except Exception:
                pass
            raise UserError(
                _(
                    "Impossible d'envoyer l'email de confirmation immédiatement. "
                    "Vérifiez l'adresse ou réessayez plus tard."
                )
            )

        _logger.info(
            "Code Wiki gallery envoyé immédiatement à %s "
            "(pending %s, from=%s, company=%s)",
            email_to,
            self.id,
            email_from,
            company.id,
        )

    @api.model
    def _purge_expired(self):
        now = fields.Datetime.now()
        expired = self.sudo().search([("expire_date", "<", now)], limit=200)
        if expired:
            expired.unlink()

    @api.model
    def find_valid(self, token):
        token = (token or "").strip()
        if not token:
            return self.browse()
        self._purge_expired()
        pending = self.sudo().search([("token", "=", token)], limit=1)
        if not pending:
            return pending
        if pending.expire_date and pending.expire_date < fields.Datetime.now():
            pending.unlink()
            return self.browse()
        return pending

    def confirm_with_code(self, raw_code):
        """Valide le code ; crée la contribution ou supprime le dépôt."""
        self.ensure_one()
        code = (raw_code or "").strip()
        if self.expire_date and self.expire_date < fields.Datetime.now():
            self.unlink()
            return {
                "ok": False,
                "error": "expired",
                "message": _("Le code a expiré. Veuillez renvoyer votre contribution."),
            }
        if code != (self.code or ""):
            self.attempts += 1
            if self.attempts >= _MAX_ATTEMPTS:
                self.unlink()
                return {
                    "ok": False,
                    "error": "too_many_attempts",
                    "message": _(
                        "Trop de tentatives incorrectes. "
                        "La contribution a été annulée."
                    ),
                    "deleted": True,
                }
            remaining = _MAX_ATTEMPTS - self.attempts
            return {
                "ok": False,
                "error": "bad_code",
                "message": _(
                    "Code incorrect. Il vous reste %(n)s tentative(s)."
                )
                % {"n": remaining},
            }

        vals = {
            "gallery_id": self.gallery_id.id,
            "text": self.text,
            "image": self.image,
            "state": "submitted",
            "contributor_name": self.contributor_name or False,
            "contributor_email": self.contributor_email,
            "name": self.name,
        }
        stored = self.with_context(bin_size=False)
        if stored.media_mimetype and stored.media:
            vals.update(
                {
                    "media": stored.media,
                    "media_filename": stored.media_filename,
                    "media_mimetype": stored.media_mimetype,
                }
            )
        item = self.env["wiki.gallery.item"].sudo().create(vals)
        self.env["wiki.gallery.verified.email"].sudo().remember(
            self.contributor_email,
            self.website_id,
        )
        self.unlink()
        return {
            "ok": True,
            "id": item.id,
            "message": _(
                "Merci ! Votre contribution a bien été envoyée. "
                "Elle sera visible après validation."
            ),
        }

    def cancel_pending(self):
        self.ensure_one()
        self.unlink()
        return {
            "ok": True,
            "deleted": True,
            "message": _("Contribution annulée."),
        }
