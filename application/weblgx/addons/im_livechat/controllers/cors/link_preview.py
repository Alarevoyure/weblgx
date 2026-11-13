# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

from weblgx.http import route
from weblgx.addons.mail.controllers.link_preview import LinkPreviewController
from weblgx.addons.im_livechat.tools.misc import force_guest_env


class LivechatLinkPreviewController(LinkPreviewController):
    @route("/im_livechat/cors/link_preview", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_link_preview(self, guest_token, message_id, clear=None):
        force_guest_env(guest_token)
        self.mail_link_preview(message_id, clear)

    @route("/im_livechat/cors/link_preview/delete", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_link_preview_delete(self, guest_token, link_preview_ids):
        force_guest_env(guest_token)
        self.mail_link_preview_delete(link_preview_ids)
