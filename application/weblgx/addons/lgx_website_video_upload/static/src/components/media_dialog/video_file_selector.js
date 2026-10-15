/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Attachment, FileSelector, IMAGE_MIMETYPES } from "@web_editor/components/media_dialog/file_selector";

export const VIDEO_MIMETYPES = [
    "video/mp4",
    "video/webm",
    "video/ogg",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
];

export const VIDEO_EXTENSIONS = [".mp4", ".webm", ".ogg", ".ogv", ".mov", ".avi", ".mkv"];

export class VideoFileAttachment extends Attachment {}
VideoFileAttachment.template = "lgx_website_video_upload.VideoFileAttachment";
VideoFileAttachment.components = { ...Attachment.components };

/**
 * Media-dialog tab: upload / pick local video files (attachment),
 * similar to images / documents.
 */
export class VideoFileSelector extends FileSelector {
    setup() {
        super.setup();
        this.uploadText = _t("Upload a video");
        this.urlPlaceholder = "https://www.example.com/video.mp4";
        this.addText = _t("Add URL");
        this.searchPlaceholder = _t("Search a video");
        this.allLoadedText = _t("All videos have been loaded");
        this.urlWarningTitle = _t("Only video files are accepted (mp4, webm, ogg, mov…)");
        this.fileMimetypes = VIDEO_MIMETYPES.join(",");
    }

    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push(["mimetype", "in", VIDEO_MIMETYPES]);
        // Exclude assets bundles.
        domain.unshift("&", "|", ["url", "=", null], "!", ["url", "=like", "/web/assets/%"]);
        // Images are never videos; keep domain consistent if IMAGE filter leaked.
        domain.push(["mimetype", "not in", IMAGE_MIMETYPES]);
        return domain;
    }

    validateUrl(url) {
        const path = (url || "").split("?")[0].toLowerCase();
        const isValidUrl = /^.+\..+$/.test(path);
        const isValidFileFormat = VIDEO_EXTENSIONS.some((ext) => path.endsWith(ext));
        return { isValidUrl, isValidFileFormat, path };
    }

    async onClickDocument(document) {
        this.selectAttachment(document);
        await this.props.save();
    }

    async fetchAttachments(...args) {
        const attachments = await super.fetchAttachments(...args);
        if (this.selectInitialMedia()) {
            const mediaSrc = (
                this.props.media.dataset?.oeExpression ||
                this.props.media.querySelector?.(":scope > video")?.getAttribute("src") ||
                ""
            ).replace(/[?].*/, "");
            for (const attachment of attachments) {
                if (`/web/content/${attachment.id}` === mediaSrc) {
                    this.selectAttachment(attachment);
                }
            }
        }
        return attachments;
    }

    /**
     * Insert a responsive native <video> (not an iframe), so it is not
     * destroyed by website's generateVideoIframe() helper.
     */
    static async createElements(selectedMedia, { orm }) {
        return Promise.all(
            selectedMedia.map(async (attachment) => {
                let src = `/web/content/${encodeURIComponent(attachment.id)}?unique=${encodeURIComponent(attachment.checksum || "")}`;
                if (!attachment.public) {
                    let accessToken = attachment.access_token;
                    if (!accessToken) {
                        [accessToken] = await orm.call(
                            "ir.attachment",
                            "generate_access_token",
                            [attachment.id]
                        );
                    }
                    src += `&access_token=${encodeURIComponent(accessToken)}`;
                }
                const div = document.createElement("div");
                div.classList.add("media_video_upload");
                div.dataset.oeExpression = src;
                div.dataset.mimetype = attachment.mimetype || "video/mp4";
                div.setAttribute("contenteditable", "false");
                div.innerHTML = `
                    <div class="css_editable_mode_display"></div>
                    <div class="media_video_upload_size" contenteditable="false"></div>
                    <video controls playsinline preload="metadata" contenteditable="false"></video>
                `;
                const videoEl = div.querySelector("video");
                videoEl.src = src;
                videoEl.setAttribute("aria-label", attachment.name || _t("Video"));
                return div;
            })
        );
    }
}

VideoFileSelector.mediaSpecificClasses = ["media_video_upload"];
VideoFileSelector.mediaSpecificStyles = [];
VideoFileSelector.mediaExtraClasses = [];
VideoFileSelector.tagNames = ["VIDEO", "DIV"];
VideoFileSelector.attachmentsListTemplate = "lgx_website_video_upload.VideosListTemplate";
VideoFileSelector.components = {
    ...FileSelector.components,
    VideoFileAttachment,
};
