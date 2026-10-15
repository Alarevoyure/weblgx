/** @odoo-module **/

import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import options from "@web_editor/js/editor/snippets.options";

const DEFAULT_IMAGE = "/wiki_knowledge/static/src/img/wiki_logo.png";

options.registry.WikiLatestArticles = options.Class.extend({
    /**
     * Ouvre le sélecteur d'images pour définir l'illustration de repli.
     *
     * @see this.selectClass for parameters
     */
    setDefaultImage() {
        const media = document.createElement("img");
        media.src = this.$target[0].dataset.defaultImage || DEFAULT_IMAGE;
        this.call("dialog", "add", MediaDialog, {
            noDocuments: true,
            noVideos: true,
            noIcons: true,
            media,
            save: (el) => {
                const src = el.getAttribute("src") || el.src || "";
                if (src) {
                    this.$target[0].dataset.defaultImage = src;
                    this.trigger_up("widgets_start_request", {
                        $target: this.$target,
                        editableMode: true,
                    });
                }
            },
        });
    },

    /**
     * Remet wiki_logo.png comme image de repli.
     *
     * @see this.selectClass for parameters
     */
    resetDefaultImage() {
        this.$target[0].dataset.defaultImage = DEFAULT_IMAGE;
        this.trigger_up("widgets_start_request", {
            $target: this.$target,
            editableMode: true,
        });
    },

    /**
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (params.attributeName === "limit") {
            await this.trigger_up("widgets_start_request", {
                $target: this.$target,
                editableMode: true,
            });
        }
    },
});

export default {
    WikiLatestArticles: options.registry.WikiLatestArticles,
};
