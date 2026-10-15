# -*- coding: utf-8 -*-
import base64
import os
import re

from weblgx import _, http, tools
from weblgx.exceptions import UserError
from weblgx.http import request

# ~5 Mo une fois décodé
_MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_AUDIO_BYTES = 20 * 1024 * 1024
_MAX_VIDEO_BYTES = 50 * 1024 * 1024
_MAX_TEXT_LEN = 5000
_MAX_HTML_LEN = 20000
_DATA_URL_RE = re.compile(
    r"^data:image/(png|jpe?g|gif|webp);base64,(.+)$",
    re.IGNORECASE | re.DOTALL,
)
_MEDIA_NAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def _is_mp3(raw):
    if raw.startswith(b"ID3"):
        return True
    return len(raw) >= 2 and raw[0] == 0xFF and (raw[1] & 0xE0) == 0xE0


def _ftyp_brand(raw):
    if len(raw) >= 12 and raw[4:8] == b"ftyp":
        return raw[8:12]
    return None


def _safe_media_filename(filename, ext):
    base = os.path.basename(filename or "").replace("\x00", "")
    base = _MEDIA_NAME_RE.sub("_", base).strip(" .")[:120]
    if not base.lower().endswith("." + ext):
        stem = base.rsplit(".", 1)[0] if "." in base else base
        base = f"{stem or 'media'}.{ext}"
    return base


def _classify_media(raw, filename):
    """Retourne (error_dict|None, vals). MP4 = vidéo 50 Mo, MP3/M4A = audio 20 Mo."""
    if not raw:
        return None, {}
    name = (filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext == "mp3" and _is_mp3(raw):
        kind, mime, limit = "audio", "audio/mpeg", _MAX_AUDIO_BYTES
        label = _("La piste audio est trop volumineuse (max. 20 Mo).")
    elif ext == "m4a" and _ftyp_brand(raw) and _ftyp_brand(raw) != b"qt  ":
        kind, mime, limit = "audio", "audio/mp4", _MAX_AUDIO_BYTES
        label = _("La piste audio est trop volumineuse (max. 20 Mo).")
    elif ext == "mp4" and _ftyp_brand(raw) and _ftyp_brand(raw) != b"qt  ":
        kind, mime, limit = "video", "video/mp4", _MAX_VIDEO_BYTES
        label = _("La vidéo est trop volumineuse (max. 50 Mo).")
    else:
        return {
            "error": "bad_media_type",
            "message": _("Formats acceptés : MP4 (vidéo), MP3 ou M4A (audio)."),
        }, {}
    if len(raw) > limit:
        return {"error": "media_too_large", "message": label}, {}
    return None, {
        "media": base64.b64encode(raw),
        "media_filename": _safe_media_filename(filename, ext),
        "media_mimetype": mime,
        "media_kind": kind,
    }


class WikiGalleryController(http.Controller):

    def _current_website(self):
        website = getattr(request, "website", False)
        if website:
            return website
        return request.env["website"].get_current_website()

    def _parse_gallery_id(self, raw):
        try:
            return int(raw) if raw else None
        except (TypeError, ValueError):
            return None

    def _get_gallery_for_website(self, gallery_id, website):
        if not gallery_id or not website:
            return request.env["wiki.gallery"]
        return (
            request.env["wiki.gallery"]
            .sudo()
            .search(
                [
                    ("id", "=", gallery_id),
                    ("website_id", "=", website.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
        )

    def _wiki_can_skip_email_verification(self):
        """Comptes avec droits d'édition Wiki : dépôt direct."""
        user = request.env.user
        if user._is_public():
            return False
        return (
            user.has_group("wiki_knowledge.group_wiki_user")
            or user.has_group("wiki_knowledge.group_wiki_reviewer")
            or user.has_group("wiki_knowledge.group_wiki_manager")
            or user.has_group("base.group_system")
        )

    def _can_manage_gallery(self):
        user = request.env.user
        return (
            user.has_group("base.group_system")
            or user.has_group("website.group_website_designer")
            or user.has_group("wiki_knowledge.group_wiki_reviewer")
            or user.has_group("wiki_knowledge.group_wiki_manager")
        )

    def _parse_submission_payload(
        self,
        text=None,
        image_data=None,
        image_raw=None,
        media_raw=None,
        media_filename=None,
        contributor_name=None,
        contributor_email=None,
        name=None,
        gallery_id=None,
        **kw,
    ):
        """Valide le dépôt et renvoie (error_dict|None, vals|None, gallery)."""
        website = self._current_website()
        if not website:
            return {"error": "no_website", "message": _("Site web introuvable.")}, None, None

        gid = self._parse_gallery_id(gallery_id or kw.get("gallery_id"))
        gallery = self._get_gallery_for_website(gid, website)
        if not gallery:
            return (
                {
                    "error": "no_gallery",
                    "message": _(
                        "Cette bibliothèque n'est pas configurée. "
                        "Choisissez une bibliothèque dans les options du bloc."
                    ),
                },
                None,
                None,
            )

        title = (name or "").strip()[:120]
        if not title:
            return {"error": "empty_title", "message": _("Le titre est obligatoire.")}, None, None

        email = (contributor_email or kw.get("email") or "").strip()[:120]
        if not email:
            return {"error": "empty_email", "message": _("L'email est obligatoire.")}, None, None
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return {
                "error": "bad_email",
                "message": _("Veuillez saisir une adresse email valide."),
            }, None, None

        Item = request.env["wiki.gallery.item"]
        text = Item._sanitize_contribution_html(text or "")
        plain = tools.html2plaintext(text or "").strip()
        if not plain:
            return {"error": "empty_text", "message": _("Le texte est obligatoire.")}, None, None
        if len(plain) > _MAX_TEXT_LEN or len(text) > _MAX_HTML_LEN:
            return {
                "error": "text_too_long",
                "message": _("Le texte est trop long (max. %s caractères).")
                % _MAX_TEXT_LEN,
            }, None, None

        raw = image_raw if image_raw is not None else b""
        if image_raw is None:
            image_data = (image_data or "").strip()
            if not image_data:
                return {"error": "empty_image", "message": _("La photo est obligatoire.")}, None, None
            match = _DATA_URL_RE.match(image_data)
            if match:
                b64_payload = match.group(2)
            else:
                b64_payload = re.sub(r"\s+", "", image_data)
            try:
                raw = base64.b64decode(b64_payload, validate=False)
            except Exception:
                return {"error": "bad_image", "message": _("Format d'image invalide.")}, None, None

        if not raw:
            return {"error": "empty_image", "message": _("La photo est obligatoire.")}, None, None
        if len(raw) > _MAX_IMAGE_BYTES:
            return {
                "error": "image_too_large",
                "message": _("L'image est trop volumineuse (max. 5 Mo)."),
            }, None, None
        is_jpeg = raw.startswith(b"\xff\xd8\xff")
        is_png = raw.startswith(b"\x89PNG\r\n\x1a\n")
        is_gif = raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a")
        is_webp = len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
        if not (is_jpeg or is_png or is_gif or is_webp):
            return {
                "error": "bad_image_type",
                "message": _("Formats acceptés : JPEG, PNG, GIF, WEBP."),
            }, None, None

        vals = {
            "gallery_id": gallery.id,
            "text": text,
            "image": base64.b64encode(raw),
            "contributor_name": (contributor_name or "").strip()[:120] or False,
            "contributor_email": email,
            "name": title,
        }
        if media_raw:
            media_err, media_vals = _classify_media(media_raw, media_filename)
            if media_err:
                return media_err, None, None
            media_vals.pop("media_kind", None)
            vals.update(media_vals)
        return None, vals, gallery

    @http.route(
        "/wiki/gallery/list",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def gallery_list(self, gallery_id=None, **kw):
        website = self._current_website()
        gid = self._parse_gallery_id(gallery_id or kw.get("gallery_id"))
        return request.env["wiki.gallery.item"].get_published_payload(
            gallery_id=gid, website=website
        )

    @http.route(
        "/wiki/gallery/libraries",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def gallery_libraries(self, **kw):
        """Liste des bibliothèques du site (éditeur web)."""
        website = self._current_website()
        rows = (
            request.env["wiki.gallery"]
            .sudo()
            .search_read(
                [("website_id", "=", website.id), ("active", "=", True)],
                ["id", "name"],
                order="name, id",
            )
        )
        return {"galleries": rows, "website_id": website.id}

    @http.route(
        "/wiki/gallery/purge",
        type="json",
        auth="user",
        website=True,
        methods=["POST"],
    )
    def gallery_purge(self, gallery_id=None, **kw):
        """Supprime une bibliothèque et toutes ses contributions (bloc retiré)."""
        if not self._can_manage_gallery():
            return {"error": "forbidden", "ok": False}
        website = self._current_website()
        gid = self._parse_gallery_id(gallery_id or kw.get("gallery_id"))
        if not gid or not website:
            return {"error": "invalid", "ok": False}
        gallery = (
            request.env["wiki.gallery"]
            .sudo()
            .search(
                [("id", "=", gid), ("website_id", "=", website.id)],
                limit=1,
            )
        )
        if not gallery:
            return {"ok": True, "deleted": False}
        gallery.item_ids.unlink()
        gallery.unlink()
        return {"ok": True, "deleted": True}

    def _read_upload(self, field_name):
        storage = request.httprequest.files.get(field_name)
        if not storage or not storage.filename:
            return b"", ""
        return storage.read(), storage.filename

    @http.route(
        "/wiki/gallery/submit",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=True,
        max_content_length=60 * 1024 * 1024,
    )
    def gallery_submit(self, **post):
        """Dépôt public. Le code part tout de suite, sauf éditeur ou adresse déjà confirmée."""
        image_raw, _image_name = self._read_upload("image")
        media_raw, media_filename = self._read_upload("media")
        err, vals, gallery = self._parse_submission_payload(
            text=post.get("text"),
            image_raw=image_raw,
            media_raw=media_raw,
            media_filename=media_filename,
            contributor_name=post.get("contributor_name"),
            contributor_email=post.get("contributor_email"),
            name=post.get("name"),
            gallery_id=post.get("gallery_id"),
        )
        if err:
            return request.make_json_response(err)

        already_verified = request.env["wiki.gallery.verified.email"].sudo().is_verified(
            vals.get("contributor_email"),
            gallery.website_id,
        )
        if self._wiki_can_skip_email_verification() or already_verified:
            item_vals = dict(vals)
            item_vals["state"] = "submitted"
            item = request.env["wiki.gallery.item"].sudo().create(item_vals)
            return request.make_json_response(
                {
                    "ok": True,
                    "id": item.id,
                    "verified": True,
                    "message": _(
                        "Merci ! Votre contribution a bien été envoyée. "
                        "Elle sera visible après validation."
                    ),
                }
            )

        try:
            pending = request.env["wiki.gallery.pending"].sudo().create_pending(vals)
        except UserError as exc:
            return request.make_json_response(
                {"error": "mail_failed", "message": str(exc)}
            )
        except Exception:
            return request.make_json_response(
                {
                    "error": "mail_failed",
                    "message": _(
                        "Impossible d'envoyer l'email de confirmation. "
                        "Vérifiez l'adresse ou réessayez plus tard."
                    ),
                }
            )

        return request.make_json_response(
            {
                "ok": True,
                "needs_verification": True,
                "token": pending.token,
                "email": pending.contributor_email,
                "message": _(
                    "Un code de confirmation a été envoyé à %(email)s. "
                    "Saisissez-le ci-dessous pour finaliser l'envoi."
                )
                % {"email": pending.contributor_email},
            }
        )

    @http.route(
        "/wiki/gallery/verify",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def gallery_verify(self, token=None, code=None, **kw):
        """Confirme le code reçu par email → crée la contribution ou annule."""
        Pending = request.env["wiki.gallery.pending"].sudo()
        pending = Pending.find_valid(token or kw.get("token"))
        if not pending:
            return {
                "ok": False,
                "error": "not_found",
                "message": _(
                    "Demande introuvable ou expirée. "
                    "Veuillez renvoyer votre contribution."
                ),
                "deleted": True,
            }
        website = self._current_website()
        if website and pending.website_id and pending.website_id.id != website.id:
            return {
                "ok": False,
                "error": "wrong_website",
                "message": _("Cette confirmation ne correspond pas à ce site."),
            }
        return pending.confirm_with_code(code or kw.get("code"))

    @http.route(
        "/wiki/gallery/verify/cancel",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def gallery_verify_cancel(self, token=None, **kw):
        """Annule un dépôt en attente de confirmation."""
        Pending = request.env["wiki.gallery.pending"].sudo()
        pending = Pending.find_valid(token or kw.get("token"))
        if not pending:
            return {
                "ok": True,
                "deleted": True,
                "message": _("Contribution annulée."),
            }
        return pending.cancel_pending()
