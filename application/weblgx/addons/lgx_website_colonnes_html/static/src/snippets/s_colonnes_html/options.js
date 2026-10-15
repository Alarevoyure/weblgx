/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import options from "@web_editor/js/editor/snippets.options";
import { _t } from "@web/core/l10n/translation";
import { cloneContentEls } from "@website/js/utils";
import { Component, useState } from "@odoo/owl";

const PLACEHOLDER_HTML = `
<div class="s_colonnes_html_placeholder font-monospace p-3">
Colonne — cliquez sur « Modifier le code » pour coller votre HTML.
</div>`.trim();

class ColonnesHtmlCodeDialog extends Component {
    static template = "lgx_website_colonnes_html.s_colonnes_html_dialog";
    static components = { Dialog, CodeEditor };
    setup() {
        this.state = useState({ value: this.props.value });
    }
    onCodeChange(newValue) {
        this.state.value = newValue;
    }
    onConfirm() {
        this.props.confirm(this.state.value);
        this.props.close();
    }
}

/**
 * Options on the whole snippet: column count (1–6).
 */
options.registry.ColonnesHtml = options.Class.extend({
    /**
     * @override
     */
    cleanForSave() {
        for (const colEl of this.$target[0].querySelectorAll(".s_colonnes_html_col")) {
            const templateEl = colEl.querySelector(":scope > template.s_colonnes_html_saved");
            const embeddedEl = colEl.querySelector(":scope > .s_colonnes_html_embedded");
            if (templateEl && embeddedEl) {
                embeddedEl.replaceChildren(cloneContentEls(templateEl.content, true));
            }
        }
    },

    /**
     * @see this.selectClass for parameters
     */
    async selectCount(previewMode, widgetValue) {
        const count = Math.min(6, Math.max(1, parseInt(widgetValue, 10) || 1));
        const rowEl = this.$target[0].querySelector(".s_colonnes_html_row");
        if (!rowEl) {
            return;
        }
        let cols = [...rowEl.querySelectorAll(":scope > .s_colonnes_html_col")];
        while (cols.length < count) {
            if (!cols.length) {
                rowEl.appendChild(this._createEmptyColumn(1));
            } else {
                const clone = cols[cols.length - 1].cloneNode(true);
                this._resetColumnContent(clone, cols.length + 1);
                rowEl.appendChild(clone);
            }
            cols = [...rowEl.querySelectorAll(":scope > .s_colonnes_html_col")];
        }
        while (cols.length > count) {
            cols[cols.length - 1].remove();
            cols = [...rowEl.querySelectorAll(":scope > .s_colonnes_html_col")];
        }
        await new Promise((resolve) => setTimeout(resolve));
        this.trigger_up("activate_snippet", {
            $snippet: this.$(cols[0] || this.$target),
        });
    },

    /**
     * @private
     * @param {number} index
     * @returns {HTMLElement}
     */
    _createEmptyColumn(index) {
        const col = document.createElement("div");
        col.className = "col-12 col-lg s_colonnes_html_col";
        col.dataset.name = "Colonne HTML";
        this._resetColumnContent(col, index);
        return col;
    },

    /**
     * @private
     * @param {HTMLElement} colEl
     * @param {number} index
     */
    _resetColumnContent(colEl, index) {
        const html = PLACEHOLDER_HTML.replace(
            "Colonne —",
            `Colonne ${index} —`
        );
        let templateEl = colEl.querySelector(":scope > template.s_colonnes_html_saved");
        if (!templateEl) {
            templateEl = document.createElement("template");
            templateEl.classList.add("s_colonnes_html_saved");
            colEl.prepend(templateEl);
        }
        templateEl.content.replaceChildren(cloneContentEls(html, true));

        let embeddedEl = colEl.querySelector(":scope > .s_colonnes_html_embedded");
        if (!embeddedEl) {
            embeddedEl = document.createElement("div");
            embeddedEl.className = "s_colonnes_html_embedded o_not_editable";
            embeddedEl.setAttribute("contenteditable", "false");
            embeddedEl.setAttribute("data-oe-protected", "true");
            colEl.appendChild(embeddedEl);
        }
        embeddedEl.replaceChildren(cloneContentEls(html));
    },

    /**
     * @override
     */
    _computeWidgetState(methodName) {
        if (methodName === "selectCount") {
            const rowEl = this.$target[0].querySelector(".s_colonnes_html_row");
            if (!rowEl) {
                return "3";
            }
            return String(rowEl.querySelectorAll(":scope > .s_colonnes_html_col").length);
        }
        return this._super(...arguments);
    },
});

/**
 * Options on one column: open Ace HTML editor.
 */
options.registry.ColonnesHtmlColumn = options.Class.extend({
    init() {
        this._super(...arguments);
        this.dialog = this.bindService("dialog");
    },

    /**
     * Before save, push template → embedded so SVG/raw HTML survive
     * the editor sanitizer that may have altered the live DOM.
     *
     * @override
     */
    cleanForSave() {
        const colEl = this.$target[0];
        const templateEl = colEl.querySelector(":scope > template.s_colonnes_html_saved");
        const embeddedEl = colEl.querySelector(":scope > .s_colonnes_html_embedded");
        if (templateEl && embeddedEl) {
            embeddedEl.replaceChildren(cloneContentEls(templateEl.content, true));
        }
    },

    /**
     * Open the code editor for the selected column.
     */
    async editCode() {
        const colEl = this.$target[0];
        let templateEl = colEl.querySelector(":scope > template.s_colonnes_html_saved");
        const embeddedEl = colEl.querySelector(":scope > .s_colonnes_html_embedded");
        if (!embeddedEl) {
            return;
        }
        if (!templateEl) {
            templateEl = document.createElement("template");
            templateEl.classList.add("s_colonnes_html_saved");
            templateEl.content.append(cloneContentEls(embeddedEl, true));
            colEl.prepend(templateEl);
        }
        // Prefer template content (source of truth); fall back to live DOM.
        const embedContent = (templateEl.innerHTML || embeddedEl.innerHTML).trim();

        await new Promise((resolve) => {
            this.dialog.add(ColonnesHtmlCodeDialog, {
                title: _t("Modifier le code HTML"),
                value: embedContent,
                mode: "xml",
                confirm: (newValue) => {
                    // Keep full markup (incl. SVG) in the template; show a
                    // script-free copy in the live DOM during edition.
                    templateEl.content.replaceChildren(cloneContentEls(newValue, true));
                    embeddedEl.replaceChildren(cloneContentEls(newValue));
                },
            }, {
                onClose: resolve,
            });
        });
    },
});

export default {
    ColonnesHtml: options.registry.ColonnesHtml,
    ColonnesHtmlColumn: options.registry.ColonnesHtmlColumn,
};
