# -*- coding: utf-8 -*-

import re
from urllib.parse import unquote

from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.translate import _

from odoo.addons.web_editor.controllers.main import Web_Editor as WebEditorController
from odoo.addons.web_editor.controllers.main import get_existing_attachment


class WebEditor(WebEditorController):

    def _resolve_website_id_for_upload(self, website_id=None):
        """Resolve the website being edited for media uploads."""
        if website_id:
            return int(website_id)
        ctx_id = request.env.context.get("website_id")
        if ctx_id:
            return int(ctx_id)
        referer = unquote(request.httprequest.referrer or "")
        if referer:
            match = re.search(r"website_id=(\d+)", referer)
            if match:
                return int(match.group(1))
        return None

    def _get_upload_website(self):
        website_id = self._resolve_website_id_for_upload()
        if website_id:
            website = request.env["website"].browse(website_id).exists()
            if website:
                return website
        return request.env["website"].get_current_website(fallback=False)

    def add_data(
        self,
        name,
        data,
        is_image,
        quality=0,
        width=0,
        height=0,
        res_id=False,
        res_model="ir.ui.view",
        website_id=None,
        **kwargs,
    ):
        resolved = self._resolve_website_id_for_upload(website_id)
        if resolved:
            request.update_env(context=dict(request.env.context, website_id=resolved))
        return super().add_data(
            name=name,
            data=data,
            is_image=is_image,
            quality=quality,
            width=width,
            height=height,
            res_id=res_id,
            res_model=res_model,
            **kwargs,
        )

    def add_url(self, url, res_id=False, res_model="ir.ui.view", website_id=None, **kwargs):
        resolved = self._resolve_website_id_for_upload(website_id)
        if resolved:
            request.update_env(context=dict(request.env.context, website_id=resolved))
        return super().add_url(url=url, res_id=res_id, res_model=res_model, **kwargs)

    def _attachment_create(self, name="", data=False, url=False, res_id=False, res_model="ir.ui.view"):
        """Include website_id in deduplication for website media uploads."""
        IrAttachment = request.env["ir.attachment"]

        if name.lower().endswith(".bmp"):
            name = name[:-4]

        if not name and url:
            name = url.split("/").pop()

        if res_model != "ir.ui.view" and res_id:
            res_id = int(res_id)
        else:
            res_id = False

        attachment_data = {
            "name": name,
            "public": res_model == "ir.ui.view",
            "res_id": res_id,
            "res_model": res_model,
        }

        website = self._get_upload_website()
        if website and res_model == "ir.ui.view" and not res_id:
            attachment_data["website_id"] = website.id

        if data:
            attachment_data["raw"] = data
            if url:
                attachment_data["url"] = url
        elif url:
            attachment_data.update({
                "type": "url",
                "url": url,
            })
        else:
            raise UserError(_("You need to specify either data or url to create an attachment."))

        if (
            not request.env.is_admin()
            and IrAttachment._can_bypass_rights_on_media_dialog(**attachment_data)
        ):
            attachment = IrAttachment.sudo().create(attachment_data)
            if not attachment_data["public"]:
                attachment.sudo().generate_access_token()
        else:
            attachment = get_existing_attachment(IrAttachment, attachment_data) or IrAttachment.create(attachment_data)

        return attachment
