/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class WikiMediaPlayerField extends Component {
    static template = "wiki_knowledge.WikiMediaPlayerField";
    static props = { ...standardFieldProps };

    get kind() {
        const mime = (this.props.record.data.media_mimetype || "").toLowerCase();
        if (mime.startsWith("video/")) {
            return "video";
        }
        if (mime.startsWith("audio/")) {
            return "audio";
        }
        return "";
    }

    get src() {
        const id = this.props.record.resId;
        const name = this.props.record.data.media_filename || "media";
        if (!id || !this.kind) {
            return "";
        }
        return `/web/content/wiki.gallery.item/${id}/media/${encodeURIComponent(name)}`;
    }
}

registry.category("fields").add("wiki_media_player", {
    component: WikiMediaPlayerField,
    supportedTypes: ["char"],
});
