/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * Building block : affiche l'astuce DeepSeek du site courant.
 */
const AstuceSnippet = publicWidget.Widget.extend({
    selector: ".s_astuce",
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        const proms = [this._super(...arguments)];
        proms.push(this._loadAstuce());
        return Promise.all(proms);
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    async _loadAstuce() {
        const body = this.el.querySelector("[data-astuce-content]");
        if (!body) {
            return;
        }
        const rawId = this.el.dataset.astuceId;
        let astuceId = null;
        if (rawId) {
            const parsed = parseInt(rawId, 10);
            astuceId = Number.isFinite(parsed) ? parsed : null;
        }
        try {
            const res = await jsonrpc("/website/astuce/get", {astuce_id: astuceId});
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            const label = this.el.querySelector(".s_astuce_label");
            if (label && res && res.name) {
                label.textContent = res.name;
            }
            if (res && res.content) {
                body.innerHTML = "";
                const p = document.createElement("p");
                p.className = "s_astuce_text mb-0";
                p.textContent = res.content;
                body.appendChild(p);
            } else {
                body.innerHTML =
                    '<p class="s_astuce_placeholder text-muted mb-0">' +
                    "Aucune astuce disponible pour le moment." +
                    "</p>";
            }
            this.options.wysiwyg?.odooEditor?.observerActive?.();
        } catch {
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            body.innerHTML =
                '<p class="s_astuce_placeholder text-muted mb-0">' +
                "Astuce indisponible." +
                "</p>";
            this.options.wysiwyg?.odooEditor?.observerActive?.();
        }
    },
});

publicWidget.registry.AstuceSnippet = AstuceSnippet;

export default AstuceSnippet;
