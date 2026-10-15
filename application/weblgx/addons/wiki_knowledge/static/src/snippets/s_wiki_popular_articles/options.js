/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.WikiPopularArticles = options.Class.extend({
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
    WikiPopularArticles: options.registry.WikiPopularArticles,
};
