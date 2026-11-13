# -*- coding: utf-8 -*-

import base64
import binascii
import html
import json
import logging
import os
import re
from urllib.parse import quote

from odoo import http
from odoo.http import request
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

_MAX_BODY = 7_000_000
_MAX_IMAGE = 4 * 1024 * 1024
_MAX_TITLE = 500
_MAX_TEXT = 2_000
_MAX_EXTERNAL_ID = 128
_MAX_TAGS = 30
_MAX_TAG_NAME = 50
_IMAGE_MIMES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
_LEADING_BLOCK = re.compile(
    r"^\s*<(p|h1|h2|div)(?:\s[^>]*)?>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL,
)


def _json(data, status=200):
    return request.make_json_response(data, status=status)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "oui")
    return False


def _clean(value, limit):
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return " ".join(value.split())[:limit]


def _same_text(left, right):
    return " ".join((left or "").split()).casefold() == " ".join((right or "").split()).casefold()


def _plain_html(fragment):
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    return html.unescape(text)


def _strip_title_html(body, title):
    match = _LEADING_BLOCK.match(body or "")
    if match and _same_text(_plain_html(match.group(2)), title):
        return body[match.end():].lstrip()
    return body or ""


def _html_from_text(text, title):
    chunks = [part.strip() for part in re.split(r"\n\s*\n", text or "") if part.strip()]
    if chunks and _same_text(chunks[0], title):
        chunks = chunks[1:]
    return "".join(
        "<p>%s</p>" % html.escape(chunk).replace("\n", "<br/>")
        for chunk in chunks
    )


_IMAGE_TAG = re.compile(
    r'<p><img src="/web/image/\d+/[^"]*" alt="[^"]*" class="img-fluid"/></p>'
)


def _content_without_image(content):
    return _IMAGE_TAG.sub("", str(content or ""))


def _safe_filename(name, extension):
    base = os.path.basename(name or "")
    base = re.sub(r"[^A-Za-z0-9._-]", "-", base).strip(".-")[:80]
    if not base:
        base = "image" + extension
    root, ext = os.path.splitext(base)
    if ext.lower() not in _IMAGE_MIMES.values():
        base = (root or "image") + extension
    return base


class WebsiteBlogPlexiPost(http.Controller):

    @http.route(
        "/blog/plexipost/receive",
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        website=True,
        sitemap=False,
    )
    def plexipost_receive(self, **kwargs):
        if request.httprequest.method == "GET":
            return _json({
                "ok": True,
                "service": "blog",
                "method": "POST",
            })
        raw = request.httprequest.get_data(cache=False, as_text=True) or ""
        if len(raw) > _MAX_BODY:
            return _json({"ok": False, "error": "payload_too_large"}, 413)
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return _json({"ok": False, "error": "invalid_json"}, 400)
        if not isinstance(payload, dict):
            return _json({"ok": False, "error": "invalid_json"}, 400)

        website = self._authenticate()
        if not website:
            return _json({"ok": False, "error": "invalid_client"}, 401)
        if website != request.website:
            return _json({"ok": False, "error": "website_mismatch"}, 403)
        try:
            result = self._push(website, payload)
        except ValueError as error:
            return _json({"ok": False, "error": str(error)}, 400)
        return _json(result)

    def _authenticate(self):
        client_id, secret = self._credentials()
        if not client_id or not secret:
            return request.env["website"]
        website = request.env["website"].sudo().search(
            [("plexipost_client_id", "=", client_id)],
            limit=1,
        )
        if not website or not website._plexipost_secret_matches(secret):
            return request.env["website"]
        return website

    def _credentials(self):
        headers = request.httprequest.headers
        client_id = (headers.get("X-Client-Id") or "").strip()
        secret = headers.get("X-Client-Secret") or ""
        if client_id and secret:
            return client_id[:200], secret[:500]
        authorization = headers.get("Authorization") or ""
        if authorization.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(authorization.split(" ", 1)[1].strip()).decode()
            except (binascii.Error, UnicodeDecodeError, IndexError):
                return "", ""
            if ":" not in decoded:
                return "", ""
            client_id, secret = decoded.split(":", 1)
            return client_id.strip()[:200], secret[:500]
        return "", ""

    def _push(self, website, payload):
        title = _clean(payload.get("title") or payload.get("name"), _MAX_TITLE)
        if not title:
            raise ValueError("missing_title")
        external_id = self._external_id(payload)
        blog = website.sudo().plexipost_blog_id
        if not blog or blog.website_id != website:
            blog = request.env["blog.blog"].sudo().search(
                [("website_id", "=", website.id)],
                order="id",
                limit=1,
            )
        if not blog:
            raise ValueError("no_blog")

        lang = website.default_lang_id.code or "fr_FR"
        Post = request.env["blog.post"].sudo().with_context(
            lang=lang,
            website_id=website.id,
        )
        existing = Post.browse()
        if external_id:
            existing = Post.search([
                ("website_id", "=", website.id),
                ("plexipost_external_id", "=", external_id),
            ], limit=1)

        body = self._article_body(payload, title)
        image = self._prepare_image(payload)
        vals = {"name": title}
        if body is not None and image is None:
            vals["content"] = body or "<p></p>"
        if "subtitle" in payload:
            vals["subtitle"] = _clean(payload.get("subtitle"), _MAX_TEXT) or False
        if "teaser" in payload:
            vals["teaser_manual"] = _clean(payload.get("teaser"), _MAX_TEXT) or False
        if "published" in payload:
            vals["is_published"] = _as_bool(payload.get("published"))
        elif not existing:
            vals["is_published"] = False
        if "tags" in payload:
            vals["tag_ids"] = [(6, 0, self._tags(website, payload.get("tags"), lang).ids)]

        created = not bool(existing)
        if existing:
            existing.write(vals)
            post = existing
        else:
            vals.update({
                "blog_id": blog.id,
                "author_id": website.company_id.partner_id.id,
                "plexipost_external_id": external_id or False,
                "is_published": vals.get("is_published", False),
                "content": vals.get("content") or body or "<p></p>",
            })
            post = Post.create(vals)
        if body is not None or image is not None:
            image_html = self._store_image(post, website, image)
            text = body if body is not None else _content_without_image(post.content)
            post.write({"content": (text + image_html) or "<p></p>"})
        _logger.info(
            "PlexiPost article website=%s post=%s created=%s",
            website.id, post.id, created,
        )
        url = post.website_url
        if website.domain:
            url = website.domain.rstrip("/") + post.website_url
        return {
            "ok": True,
            "id": post.id,
            "external_id": post.plexipost_external_id or False,
            "url": url,
            "published": bool(post.is_published),
            "created": created,
        }

    def _external_id(self, payload):
        if payload.get("post_id") not in (None, ""):
            return _clean(payload.get("post_id"), _MAX_EXTERNAL_ID)
        return _clean(payload.get("external_id"), _MAX_EXTERNAL_ID)

    def _article_body(self, payload, title):
        body_html = payload.get("body_html")
        if isinstance(body_html, str) and body_html.strip():
            if len(body_html) > _MAX_BODY:
                raise ValueError("payload_too_large")
            return _strip_title_html(body_html.strip(), title)
        body_text = payload.get("body_text")
        if isinstance(body_text, str) and body_text.strip():
            if len(body_text) > _MAX_BODY:
                raise ValueError("payload_too_large")
            return _html_from_text(body_text, title)
        if "content" in payload or "body" in payload:
            content = payload.get("content", payload.get("body", ""))
            if content and not isinstance(content, str):
                raise ValueError("invalid_content")
            if isinstance(content, str) and len(content) > _MAX_BODY:
                raise ValueError("payload_too_large")
            return content or ""
        return None

    def _prepare_image(self, payload):
        if "image_base64" not in payload:
            return None
        encoded = payload.get("image_base64")
        if not encoded:
            return False
        if not isinstance(encoded, str):
            raise ValueError("invalid_image")
        if encoded.startswith("data:") and "," in encoded:
            encoded = encoded.split(",", 1)[1]
        encoded = "".join(encoded.split())
        try:
            raw = base64.b64decode(encoded, validate=True)
        except binascii.Error as error:
            raise ValueError("invalid_image") from error
        if not raw or len(raw) > _MAX_IMAGE:
            raise ValueError("image_too_large")
        mime = guess_mimetype(raw)
        if mime not in _IMAGE_MIMES:
            raise ValueError("invalid_image")
        return {
            "raw": raw,
            "mime": mime,
            "filename": _safe_filename(payload.get("image_filename"), _IMAGE_MIMES[mime]),
        }

    def _store_image(self, post, website, image):
        Attachment = request.env["ir.attachment"].sudo()
        previous = Attachment.search([
            ("res_model", "=", "blog.post"),
            ("res_id", "=", post.id),
            ("description", "=", "plexipost"),
        ])
        if image is None:
            return self._image_tag(previous[:1]) if previous else ""
        previous.unlink()
        attachment = Attachment.browse()
        if image:
            attachment = Attachment.with_context(website_id=website.id).create({
                "name": image["filename"],
                "datas": base64.b64encode(image["raw"]).decode(),
                "res_model": "blog.post",
                "res_id": post.id,
                "mimetype": image["mime"],
                "public": True,
                "description": "plexipost",
                "website_id": website.id,
            })
        self._set_cover(post, attachment[:1])
        return self._image_tag(attachment) if attachment else ""

    def _set_cover(self, post, attachment):
        properties = json.loads(post.cover_properties or "{}")
        if attachment:
            src = "/web/image/%s/%s" % (attachment.id, quote(attachment.name or "image"))
            properties["background-image"] = "url(%s)" % src
            properties["opacity"] = "0.6"
            resize = set((properties.get("resize_class") or "").split())
            resize.add("o_record_has_cover")
            if not resize.intersection({"o_half_screen_height", "o_full_screen_height", "cover_auto"}):
                resize.add("o_half_screen_height")
            properties["resize_class"] = " ".join(
                part for part in (
                    "o_record_has_cover",
                    "o_full_screen_height" if "o_full_screen_height" in resize else "",
                    "o_half_screen_height" if "o_half_screen_height" in resize else "",
                    "cover_auto" if "cover_auto" in resize else "",
                ) if part
            )
        else:
            properties["background-image"] = "none"
            properties["opacity"] = "0.2"
            resize = set((properties.get("resize_class") or "").split())
            resize.discard("o_record_has_cover")
            properties["resize_class"] = " ".join(resize) or "o_half_screen_height"
        properties.setdefault("background_color_class", "o_cc3")
        post.write({"cover_properties": json.dumps(properties)})

    def _image_tag(self, attachment):
        filename = quote(attachment.name or "image")
        src = "/web/image/%s/%s" % (attachment.id, filename)
        alt = html.escape(attachment.name or "", quote=True)
        return '<p><img src="%s" alt="%s" class="img-fluid"/></p>' % (html.escape(src, quote=True), alt)

    def _tags(self, website, names, lang):
        Tag = request.env["blog.tag"].sudo().with_context(lang=lang)
        tags = Tag.browse()
        if not isinstance(names, list):
            raise ValueError("invalid_tags")
        for name in names[:_MAX_TAGS]:
            clean = _clean(name, _MAX_TAG_NAME)
            if not clean:
                continue
            tag = Tag.search([
                ("name", "=", clean),
                ("website_id", "=", website.id),
            ], limit=1)
            if not tag:
                tag = Tag.create({"name": clean, "website_id": website.id})
            tags |= tag
        return tags
