/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { cloneContentEls } from "@website/js/utils";

const ColonnesHtmlWidget = publicWidget.Widget.extend({
    selector: ".s_colonnes_html",
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        this.columnEls = [...this.el.querySelectorAll(".s_colonnes_html_col")];
        for (const colEl of this.columnEls) {
            this._ensureSavedTemplate(colEl);
            this._restoreEmbeddedFromTemplate(colEl);
            const embeddedEl = colEl.querySelector(".s_colonnes_html_embedded");
            if (this.editableMode && embeddedEl && embeddedEl.offsetHeight === 0) {
                const placeholderEl = document.createElement("div");
                placeholderEl.classList.add(
                    "s_colonnes_html_placeholder",
                    "alert",
                    "alert-info",
                    "pt16",
                    "pb16",
                    "mb-0"
                );
                placeholderEl.textContent = _t(
                    "Cette colonne HTML est vide. Cliquez sur « Modifier le code » pour l'éditer."
                );
                embeddedEl.appendChild(placeholderEl);
            }
        }
        return this._super(...arguments);
    },

    /**
     * @private
     * @param {HTMLElement} colEl
     */
    _ensureSavedTemplate(colEl) {
        if (colEl.querySelector(":scope > template.s_colonnes_html_saved")) {
            return;
        }
        const embeddedEl = colEl.querySelector(".s_colonnes_html_embedded");
        if (!embeddedEl) {
            return;
        }
        const templateEl = document.createElement("template");
        templateEl.classList.add("s_colonnes_html_saved");
        templateEl.content.append(cloneContentEls(embeddedEl, true));
        colEl.prepend(templateEl);
    },

    /**
     * Always display the template content (preserves SVG / raw HTML).
     * Scripts are omitted in edit mode.
     *
     * @private
     * @param {HTMLElement} colEl
     */
    _restoreEmbeddedFromTemplate(colEl) {
        const templateEl = colEl.querySelector(":scope > template.s_colonnes_html_saved");
        const embeddedEl = colEl.querySelector(":scope > .s_colonnes_html_embedded");
        if (!templateEl || !embeddedEl) {
            return;
        }
        embeddedEl.replaceChildren(
            cloneContentEls(templateEl.content, !this.editableMode)
        );
    },

    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        if (!this.editableMode) {
            for (const colEl of this.columnEls || []) {
                this._restoreEmbeddedFromTemplate(colEl);
            }
        }
    },
});

publicWidget.registry.ColonnesHtml = ColonnesHtmlWidget;

export default ColonnesHtmlWidget;
