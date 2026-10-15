/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { MediaDialog, TABS } from "@web_editor/components/media_dialog/media_dialog";
import { VideoFileSelector } from "./video_file_selector";

TABS.LOCAL_VIDEOS = {
    id: "LOCAL_VIDEOS",
    title: _t("Uploaded videos"),
    Component: VideoFileSelector,
};

patch(MediaDialog.prototype, {
    /**
     * @override
     */
    addTabs() {
        super.addTabs(...arguments);
        // Background-video picker stays URL-only (autoplay platforms).
        if (this.props.isForBgVideo) {
            return;
        }
        if (this.tabs.some((tab) => tab.id === TABS.VIDEOS.id)) {
            this.addTab(TABS.LOCAL_VIDEOS);
        }
    },

    /**
     * @override
     * Prefer the upload tab when editing an already uploaded video.
     */
    get initialActiveTab() {
        if (this.props.media?.classList?.contains("media_video_upload")) {
            return TABS.LOCAL_VIDEOS.id;
        }
        return super.initialActiveTab;
    },

    /**
     * @override
     */
    async renderMedia(selectedMedia) {
        const elements = await super.renderMedia(...arguments);
        if (this.state.activeTab === TABS.LOCAL_VIDEOS.id && this.props.media) {
            const parentEl = this.props.media.parentElement;
            if (
                parentEl &&
                parentEl.tagName === "A" &&
                parentEl.children.length === 1 &&
                this.props.media.tagName === "IMG"
            ) {
                parentEl.replaceWith(parentEl.firstElementChild);
            }
        }
        return elements;
    },
});
