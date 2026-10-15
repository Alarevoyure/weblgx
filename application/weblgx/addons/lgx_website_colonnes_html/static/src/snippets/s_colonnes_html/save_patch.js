/** @odoo-module **/

import { WysiwygAdapterComponent } from "@website/components/wysiwyg_adapter/wysiwyg_adapter";
import { patch } from "@web/core/utils/patch";
import { cloneContentEls } from "@website/js/utils";

/**
 * Restore each column's visible HTML from its <template> before save.
 * The editor sanitizer can strip/neutralize raw <svg> in the live DOM;
 * the template is the source of truth (same pattern as s_embed_code).
 */
function restoreColonnesHtmlFromTemplates(rootEl) {
    for (const colEl of rootEl.querySelectorAll(".s_colonnes_html_col")) {
        const templateEl = colEl.querySelector(":scope > template.s_colonnes_html_saved");
        const embeddedEl = colEl.querySelector(":scope > .s_colonnes_html_embedded");
        if (templateEl && embeddedEl) {
            embeddedEl.replaceChildren(cloneContentEls(templateEl.content, true));
        }
    }
}

patch(WysiwygAdapterComponent.prototype, {
    /**
     * @override
     */
    async _saveElement($el, context, withLang, ...rest) {
        if ($el[0]?.querySelector?.(".s_colonnes_html")) {
            const $clonedEl = $el.clone(true, true);
            restoreColonnesHtmlFromTemplates($clonedEl[0]);
            return super._saveElement($clonedEl, context, withLang, ...rest);
        }
        return super._saveElement($el, context, withLang, ...rest);
    },
});
