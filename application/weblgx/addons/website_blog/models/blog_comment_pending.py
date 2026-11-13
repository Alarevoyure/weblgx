# -*- coding: utf-8 -*-
import hmac
import logging
import re
import secrets
from datetime import timedelta
from email.utils import make_msgid

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import email_domain_extract, email_normalize, plaintext2html
from odoo.tools.misc import html_escape

_logger = logging.getLogger(__name__)

_CODE_TTL_MINUTES = 20
_MAX_ATTEMPTS = 5
_MAX_MESSAGE = 4000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class BlogCommentPending(models.Model):
    _name = "blog.comment.pending"
    _description = "Blog comment waiting for an email code"
    _order = "id desc"

    token = fields.Char(required=True, index=True, copy=False)
    code = fields.Char(required=True, copy=False, groups="base.group_system")
    email = fields.Char(required=True, index=True)
    body = fields.Text(required=True)
    blog_post_id = fields.Many2one(
        "blog.post",
        required=True,
        ondelete="cascade",
        index=True,
    )
    website_id = fields.Many2one(
        "website",
        required=True,
        ondelete="cascade",
        index=True,
    )
    attempts = fields.Integer(default=0)
    expire_date = fields.Datetime(required=True, index=True)

    _sql_constraints = [
        ("token_uniq", "unique(token)", "The confirmation token must be unique."),
    ]

    @api.model
    def _normalize_email(self, email):
        return (email or "").strip().lower()

    @api.model
    def _generate_code(self):
        return f"{secrets.randbelow(1_000_000):06d}"

    @api.model
    def prepare_comment(self, blog_post, email, message):
        """Check the public form and return the values to store."""
        email = self._normalize_email(email)
        message = (message or "").strip()
        if not email:
            raise UserError(_("The email address is required."))
        if not _EMAIL_RE.match(email) or len(email) > 120:
            raise UserError(_("Please enter a valid email address."))
        if not message:
            raise UserError(_("The message is required."))
        if len(message) > _MAX_MESSAGE:
            raise UserError(_("The message is too long."))
        if not blog_post or not blog_post.exists() or not blog_post.is_published:
            raise UserError(_("This article cannot receive a comment."))
        website = blog_post.website_id
        recent = self.sudo().search_count([
            ("email", "=", email),
            ("website_id", "=", website.id),
            ("create_date", ">=", fields.Datetime.now() - timedelta(hours=1)),
        ])
        if recent >= 5:
            raise UserError(_("Too many confirmation requests. Please try again later."))
        previous = self.sudo().search([
            ("email", "=", email),
            ("blog_post_id", "=", blog_post.id),
        ])
        if previous:
            previous.unlink()
        return {
            "email": email,
            "body": message,
            "blog_post_id": blog_post.id,
            "website_id": website.id,
        }

    @api.model
    def create_pending(self, vals):
        now = fields.Datetime.now()
        pending = self.sudo().create({
            **vals,
            "token": secrets.token_urlsafe(24),
            "code": self._generate_code(),
            "attempts": 0,
            "expire_date": now + timedelta(minutes=_CODE_TTL_MINUTES),
        })
        try:
            pending._send_verification_email()
        except Exception:
            pending.unlink()
            raise
        self._purge_expired()
        return pending

    def _resolve_mail_server(self, company):
        self.ensure_one()
        return self.env["ir.mail_server"].sudo()._mail_servers_for_company(company)[:1]

    def _resolve_email_from(self, company, mail_server=None):
        """Adresse que le relais transmet tout de suite.

        L'adresse de notification du domaine (notifications@...) est celle des
        envois automatiques. L'email personnel de la société, envoyé via un
        autre compte SMTP, peut être accepté puis retenu par le relais.
        """
        self.ensure_one()
        company = company.sudo()
        server = mail_server or self._resolve_mail_server(company)
        smtp_user = server.smtp_user if server else False
        candidates = (
            company.default_from_email,
            smtp_user if smtp_user and "@" in smtp_user else False,
            company.partner_id.email_formatted if company.partner_id else False,
            company.email,
        )
        for email_from in candidates:
            if email_from and "@" in email_from:
                return email_from
        return False

    def _send_verification_email(self):
        self.ensure_one()
        email_to = (self.email or "").strip()
        if not email_to:
            raise UserError(_("The email address is required."))
        company = self.website_id.company_id or self.env.company
        mail_server = self._resolve_mail_server(company)
        email_from = self._resolve_email_from(company, mail_server=mail_server)
        if not email_from:
            raise UserError(_(
                "This website has no outgoing email address. "
                "Set the company email or the alias domain."
            ))
        title = html_escape(self.blog_post_id.name or "")
        code = html_escape(self.code or "")
        body = _(
            "<p>Hello,</p>"
            "<p>You left a comment on <strong>%(title)s</strong>.</p>"
            "<p>Your confirmation code is:</p>"
            "<p style=\"font-size:28px;font-weight:700;letter-spacing:4px;\">%(code)s</p>"
            "<p>This code is valid for %(minutes)s minutes.</p>"
            "<p>If you did not write this comment, you can ignore this email.</p>"
        ) % {"title": title, "code": code, "minutes": _CODE_TTL_MINUTES}
        Mail = self.env["mail.mail"].sudo().with_company(company)
        normalized_from = email_normalize(email_from)
        from_domain = email_domain_extract(normalized_from) if normalized_from else False
        mail_vals = {
            "subject": _("Blog — Confirmation code"),
            "email_from": email_from,
            "email_to": email_to,
            "body_html": body,
            "auto_delete": True,
            # @hostname local (weblgx) est rejeté ou différé par les serveurs
            # destinataires. Le domaine d'expédition, lui, est résoluble.
            "message_id": make_msgid(domain=from_domain) if from_domain else make_msgid(),
        }
        if mail_server:
            mail_vals["mail_server_id"] = mail_server.id
        mail = Mail.create(mail_vals)
        try:
            # SMTP pendant la requête : la réponse HTTP n'est renvoyée qu'après l'acceptation.
            mail.send(raise_exception=True)
        except Exception:
            _logger.exception(
                "Blog comment code email failed for %s (pending %s, company %s)",
                email_to, self.id, company.id,
            )
            try:
                if mail.exists():
                    mail.unlink()
            except Exception:
                pass
            raise UserError(_(
                "The confirmation email could not be sent. "
                "Check the address or try again later."
            ))
        _logger.info(
            "Blog comment code sent immediately to %s from %s (pending %s, company %s)",
            email_to, normalized_from or email_from, self.id, company.id,
        )

    @api.model
    def _purge_expired(self):
        expired = self.sudo().search([
            ("expire_date", "<", fields.Datetime.now()),
        ], limit=200)
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

    def _author_partner(self):
        self.ensure_one()
        Partner = self.env["res.partner"].sudo()
        partner = Partner.search([("email", "=ilike", self.email)], limit=1)
        if partner:
            return partner
        return Partner.with_context(mail_create_nosubscribe=True).create({
            "name": self.email,
            "email": self.email,
            "company_id": self.website_id.company_id.id,
        })

    def confirm_with_code(self, raw_code):
        self.ensure_one()
        code = (raw_code or "").strip()
        if self.expire_date and self.expire_date < fields.Datetime.now():
            self.unlink()
            return {
                "ok": False,
                "error": "expired",
                "message": _("The code has expired. Please send your comment again."),
            }
        if not hmac.compare_digest(code, self.code or ""):
            self.attempts += 1
            if self.attempts >= _MAX_ATTEMPTS:
                self.unlink()
                return {
                    "ok": False,
                    "error": "too_many_attempts",
                    "message": _("Too many incorrect attempts. The comment was cancelled."),
                    "deleted": True,
                }
            return {
                "ok": False,
                "error": "bad_code",
                "message": _("Incorrect code. %(n)s attempt(s) left.") % {
                    "n": _MAX_ATTEMPTS - self.attempts,
                },
            }
        post = self.blog_post_id.sudo()
        if not post.exists() or not post.is_published or post.website_id != self.website_id:
            self.unlink()
            return {
                "ok": False,
                "error": "unavailable",
                "message": _("This article cannot receive a comment."),
                "deleted": True,
            }
        partner = self._author_partner()
        post.with_context(
            blog_comment_from_portal=True,
            mail_create_nosubscribe=True,
        ).message_post(
            body=plaintext2html(self.body),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=partner.id,
            email_from=partner.email_formatted or self.email,
            blog_comment_state="pending",
        )
        self.unlink()
        return {
            "ok": True,
            "message": _(
                "Thank you. Your comment will appear once a blog administrator has validated it."
            ),
        }
