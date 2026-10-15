/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FileSelector } from "@web_editor/components/media_dialog/file_selector";
import { ImageSelector } from "@web_editor/components/media_dialog/image_selector";

patch(FileSelector.prototype, {
    setup() {
        super.setup(...arguments);
        this.websiteService = useService("website");
    },

    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        const websiteId = this.websiteService?.currentWebsite?.id;
        if (websiteId) {
            domain.push("|", ["website_id", "=", false], ["website_id", "=", websiteId]);
        }
        return domain;
    },

    async fetchAttachments(limit, offset) {
        this.state.isFetchingAttachments = true;
        const websiteId = this.websiteService?.currentWebsite?.id;
        let attachments = [];
        try {
            attachments = await this.orm.call(
                "ir.attachment",
                "search_read",
                [],
                {
                    domain: this.attachmentsDomain,
                    fields: [
                        "name", "mimetype", "description", "checksum", "url", "type",
                        "res_id", "res_model", "public", "access_token", "image_src",
                        "image_width", "image_height", "original_id",
                    ],
                    order: "id desc",
                    limit,
                    offset,
                    context: websiteId ? { website_id: websiteId } : {},
                }
            );
            attachments.forEach((attachment) => (attachment.mediaType = "attachment"));
        } catch (e) {
            if (e.exceptionName !== "odoo.exceptions.AccessError") {
                throw e;
            }
        }
        this.state.canLoadMoreAttachments = attachments.length >= this.NUMBER_OF_ATTACHMENTS_TO_DISPLAY;
        this.state.isFetchingAttachments = false;
        return attachments;
    },
});

/**
 * ImageSelector overrides uploadFiles without calling super — ensure uploads
 * still carry the website being edited.
 *
 * Also drop the original_id filter: it hides valid user uploads (e.g. webp
 * variants) after the dialog is reopened.
 */
patch(ImageSelector.prototype, {
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        const idx = domain.findIndex(
            (term) => Array.isArray(term) && term[0] === "original_id"
        );
        if (idx !== -1) {
            domain.splice(idx, 1);
        }
        return domain;
    },

    async uploadFiles(files) {
        const websiteId = this.websiteService?.currentWebsite?.id;
        let abortFn;
        const uploadPromise = this.uploadService.uploadFiles(
            files,
            {
                resModel: this.props.resModel,
                resId: this.props.resId,
                isImage: true,
                websiteId,
            },
            (attachment) => this.onUploaded(attachment),
            (abort) => {
                abortFn = abort;
            }
        );
        this.props.setAbortUploadsCallback(() => abortFn?.());
        await uploadPromise;
    },
});
