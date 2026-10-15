/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import { jsonrpc } from "@web/core/network/rpc_service";

options.registry.Astuce = options.Class.extend({
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        await this._super(...arguments);
        const selectEl = uiFragment.querySelector('[data-name="astuce_opt"]');
        if (!selectEl) {
            return;
        }
        let rows = [];
        try {
            const res = await jsonrpc("/website/astuce/list", {});
            rows = (res && res.astuces) || [];
        } catch {
            rows = [];
        }
        rows.forEach((row) => {
            const btn = document.createElement("we-button");
            btn.dataset.selectDataAttribute = String(row.id);
            btn.textContent = row.name || `Astuce #${row.id}`;
            selectEl.appendChild(btn);
        });
    },

    /**
     * @override
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await this._super(...arguments);
        await this.trigger_up("widgets_start_request", {
            $target: this.$target,
            editableMode: true,
        });
    },
});

export default {
    Astuce: options.registry.Astuce,
};
