/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

const TEXT_VAR = "--s-ce-text-width";
const MEDIA_VAR = "--s-ce-media-width";
const DEFAULT_TEXT = 70;
const DEFAULT_MEDIA = 30;

/**
 * Box option that removes Bootstrap text-bg-* classes (e.g. text-bg-white)
 * which force a white background with !important and block Colors.
 */
options.registry.ColonnesEditablesBox = options.registry.Box.extend({
    /**
     * @private
     */
    _removeTextBgClasses() {
        const el = this.$target[0];
        if (!el) {
            return;
        }
        for (const className of [...el.classList]) {
            if (className.startsWith("text-bg-")) {
                el.classList.remove(className);
            }
        }
    },

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        if (params.cssProperty === "background-color") {
            this._removeTextBgClasses();
        }
        return this._super(...arguments);
    },
});

/**
 * Options for the main image size slider (25–100 %).
 */
options.registry.ColonnesEditablesImage = options.Class.extend({
    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (params.cssProperty === "width" && widgetValue) {
            const img = this.$target[0];
            img.style.width = widgetValue;
            img.style.maxWidth = "100%";
            img.style.height = "auto";
        }
    },
});

/**
 * Column width / height applied to the card (.s_ce_column).
 */
options.registry.ColonnesEditablesColumn = options.Class.extend({});

/**
 * Split text / media zone widths.
 * The two sliders are linked so text% + media% = 100%.
 */
options.registry.ColonnesEditablesTextMedia = options.Class.extend({
    /**
     * @private
     * @returns {HTMLElement|null}
     */
    _getTextMediaRow() {
        const el = this.$target[0];
        if (!el) {
            return null;
        }
        if (el.classList.contains("s_ce_text_media_row")) {
            return el;
        }
        return el.closest(".s_ce_text_media_row")
            || el.querySelector(".s_ce_text_media_row");
    },

    /**
     * @private
     * @param {HTMLElement} row
     * @param {string} cssVar
     * @param {number} fallback
     * @returns {number}
     */
    _readPercent(row, cssVar, fallback) {
        const raw = (row.style.getPropertyValue(cssVar)
            || getComputedStyle(row).getPropertyValue(cssVar)
            || "").trim();
        const num = parseFloat(raw);
        return Number.isFinite(num) ? num : fallback;
    },

    /**
     * @private
     * @param {HTMLElement} row
     * @param {number} textPct
     * @param {number} mediaPct
     */
    _applySplit(row, textPct, mediaPct) {
        row.style.setProperty(TEXT_VAR, `${textPct}%`);
        row.style.setProperty(MEDIA_VAR, `${mediaPct}%`);
    },

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        if (params.cssProperty !== TEXT_VAR && params.cssProperty !== MEDIA_VAR) {
            return this._super(...arguments);
        }
        const row = this._getTextMediaRow();
        if (!row || !widgetValue) {
            return;
        }
        const pct = parseFloat(widgetValue);
        if (!Number.isFinite(pct)) {
            return;
        }
        if (params.cssProperty === TEXT_VAR) {
            this._applySplit(row, pct, 100 - pct);
        } else {
            this._applySplit(row, 100 - pct, pct);
        }
        if (previewMode === false) {
            await this.updateUI();
        }
    },

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === "selectStyle"
                && (params.cssProperty === TEXT_VAR || params.cssProperty === MEDIA_VAR)) {
            const row = this._getTextMediaRow();
            if (!row) {
                return params.cssProperty === TEXT_VAR ? `${DEFAULT_TEXT}%` : `${DEFAULT_MEDIA}%`;
            }
            if (params.cssProperty === TEXT_VAR) {
                return `${this._readPercent(row, TEXT_VAR, DEFAULT_TEXT)}%`;
            }
            return `${this._readPercent(row, MEDIA_VAR, DEFAULT_MEDIA)}%`;
        }
        return this._super(...arguments);
    },
});

export default {
    ColonnesEditablesBox: options.registry.ColonnesEditablesBox,
    ColonnesEditablesImage: options.registry.ColonnesEditablesImage,
    ColonnesEditablesColumn: options.registry.ColonnesEditablesColumn,
    ColonnesEditablesTextMedia: options.registry.ColonnesEditablesTextMedia,
};
