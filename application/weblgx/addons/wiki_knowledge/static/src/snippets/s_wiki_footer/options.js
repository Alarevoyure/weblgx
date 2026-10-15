/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

/**
 * @param {Object} option
 * @returns {number|false}
 */
function websiteIdFrom(option) {
    let websiteId = false;
    option.trigger_up("context_get", {
        callback: (ctx) => {
            websiteId = ctx.website_id;
        },
    });
    return websiteId;
}

/**
 * Case à cocher persistée sur un booléen de website (isolé multi-site).
 */
const WikiWebsiteFlag = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @param {boolean|string} previewMode
     * @param {string|boolean} widgetValue
     * @param {string} fieldName
     */
    async _setFlag(previewMode, widgetValue, fieldName) {
        if (previewMode) {
            return;
        }
        const websiteId = websiteIdFrom(this);
        if (!websiteId) {
            return;
        }
        const checked = widgetValue === "true" || widgetValue === true;
        await this.orm.write("website", [websiteId], {
            [fieldName]: checked,
        });
    },

    /**
     * @param {string} fieldName
     * @returns {Promise<string>}
     */
    async _readFlag(fieldName) {
        const websiteId = websiteIdFrom(this);
        if (!websiteId) {
            return "true";
        }
        const rows = await this.orm.read("website", [websiteId], [fieldName]);
        return rows[0]?.[fieldName] ? "true" : "";
    },
});

/**
 * « Afficher sur le Wiki » : footer du site visible ou non sur /wiki.
 * Persiste website.wiki_show_site_footer.
 */
options.registry.WikiShowSiteFooter = WikiWebsiteFlag.extend({
    wikiShowSiteFooter(previewMode, widgetValue) {
        return this._setFlag(previewMode, widgetValue, "wiki_show_site_footer");
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === "wikiShowSiteFooter") {
            return this._readFlag("wiki_show_site_footer");
        }
        return this._super(...arguments);
    },
});

/**
 * « Afficher le Footer Wiki » : bandeau de liens propre au Wiki.
 * Persiste website.wiki_show_footer.
 */
options.registry.WikiShowFooter = WikiWebsiteFlag.extend({
    wikiShowFooter(previewMode, widgetValue) {
        return this._setFlag(previewMode, widgetValue, "wiki_show_footer");
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === "wikiShowFooter") {
            return this._readFlag("wiki_show_footer");
        }
        return this._super(...arguments);
    },
});
