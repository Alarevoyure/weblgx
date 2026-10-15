/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

/**
 * Color option for the chronological frieze accent (--fc-accent).
 */
options.registry.FriseChronologique = options.Class.extend({
    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        if (params.cssProperty === "--fc-accent") {
            const el = this.$target[0];
            if (widgetValue) {
                el.style.setProperty("--fc-accent", widgetValue);
            } else {
                el.style.removeProperty("--fc-accent");
            }
            return;
        }
        return this._super(...arguments);
    },

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === "selectStyle" && params.cssProperty === "--fc-accent") {
            const el = this.$target[0];
            return (
                el.style.getPropertyValue("--fc-accent").trim() ||
                getComputedStyle(el).getPropertyValue("--fc-accent").trim() ||
                "#16213e"
            );
        }
        return this._super(...arguments);
    },
});

export default {
    FriseChronologique: options.registry.FriseChronologique,
};
