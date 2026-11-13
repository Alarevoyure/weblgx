# -*- coding: utf-8 -*-

from werkzeug.exceptions import Forbidden, NotFound

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.portal.controllers.mail import PortalChatter


class BlogPortalChatter(PortalChatter):

    @http.route(["/mail/chatter_post"], type="json", methods=["POST"], auth="public", website=True)
    def portal_chatter_post(self, res_model, res_id, message, attachment_ids=None, attachment_tokens=None, **kw):
        if res_model == "blog.post":
            request.update_context(blog_comment_from_portal=True)
        result = super().portal_chatter_post(
            res_model, res_id, message,
            attachment_ids=attachment_ids,
            attachment_tokens=attachment_tokens,
            **kw,
        )
        if res_model == "blog.post" and isinstance(result, dict) and result.get("default_message_id"):
            state = request.env["mail.message"].sudo().browse(result["default_message_id"]).blog_comment_state
            if state == "pending":
                result["blog_comment_pending"] = True
        return result


class WebsiteBlogComment(http.Controller):

    @http.route("/blog/comment/moderate", type="http", auth="user", website=True, methods=["POST"], sitemap=False)
    def blog_comment_moderate(self, message_id, decision, **post):
        if decision not in ("approved", "rejected"):
            raise Forbidden()
        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            raise NotFound()
        message = request.env["mail.message"].sudo().browse(message_id).exists()
        if not message or message.model != "blog.post" or message.message_type != "comment":
            raise NotFound()
        blog_post = request.env["blog.post"].browse(message.res_id).exists()
        if not blog_post or blog_post.website_id != request.website:
            raise NotFound()
        if not blog_post._user_can_moderate_comments():
            raise Forbidden()
        if message.blog_comment_state == "pending":
            message.write({"blog_comment_state": decision})
        return request.redirect(blog_post.website_url + "#o_wblog_post_comments")

    def _public_blog_post(self, post_id):
        try:
            post_id = int(post_id)
        except (TypeError, ValueError):
            return request.env["blog.post"]
        post = request.env["blog.post"].sudo().browse(post_id).exists()
        website = request.website
        if not post or not post.is_published or post.website_id != website:
            return request.env["blog.post"]
        return post

    @http.route("/blog/comment/submit", type="json", auth="public", website=True, methods=["POST"])
    def blog_comment_submit(self, post_id=None, email=None, message=None, **kw):
        post = self._public_blog_post(post_id or kw.get("post_id"))
        if not post:
            return {"ok": False, "error": "unavailable", "message": _("This article cannot receive a comment.")}
        Pending = request.env["blog.comment.pending"].sudo()
        try:
            vals = Pending.prepare_comment(post, email or kw.get("email"), message or kw.get("message"))
            pending = Pending.create_pending(vals)
        except UserError as error:
            return {"ok": False, "error": "invalid", "message": str(error)}
        return {
            "ok": True,
            "needs_verification": True,
            "token": pending.token,
            "email": pending.email,
            "message": _(
                "A confirmation code was sent to %(email)s. Enter it below to send your comment."
            ) % {"email": pending.email},
        }

    @http.route("/blog/comment/verify", type="json", auth="public", website=True, methods=["POST"])
    def blog_comment_verify(self, token=None, code=None, **kw):
        Pending = request.env["blog.comment.pending"].sudo()
        pending = Pending.find_valid(token or kw.get("token"))
        if not pending:
            return {
                "ok": False,
                "error": "not_found",
                "message": _("This request has expired. Please send your comment again."),
                "deleted": True,
            }
        if pending.website_id != request.website:
            return {
                "ok": False,
                "error": "wrong_website",
                "message": _("This confirmation does not match this website."),
            }
        return pending.confirm_with_code(code or kw.get("code"))

    @http.route("/blog/comment/cancel", type="json", auth="public", website=True, methods=["POST"])
    def blog_comment_cancel(self, token=None, **kw):
        pending = request.env["blog.comment.pending"].sudo().find_valid(token or kw.get("token"))
        if pending and pending.website_id == request.website:
            pending.unlink()
        return {"ok": True}
