/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import { jsonrpc } from "@web/core/network/rpc_service";

options.registry.WikiGallery = options.Class.extend({
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        await this._super(...arguments);
        const selectEl = uiFragment.querySelector('[data-name="gallery_opt"]');
        if (!selectEl) {
            return;
        }
        let rows = [];
        try {
            const res = await jsonrpc("/wiki/gallery/libraries", {});
            rows = (res && res.galleries) || [];
        } catch {
            rows = [];
        }
        rows.forEach((row) => {
            const btn = document.createElement("we-button");
            btn.dataset.selectDataAttribute = String(row.id);
            btn.textContent = row.name || `Bibliothèque #${row.id}`;
            selectEl.appendChild(btn);
        });
    },

    /**
     * À la suppression du bloc : purge la bibliothèque liée (photos + textes).
     * Ne pas utiliser async/await ici : après await, this._super n'est plus une fonction
     * (mécanisme Class.extend d'Odoo / Web@LGX).
     *
     * @override
     */
    onRemove() {
        const raw = this.$target[0] && this.$target[0].dataset.galleryId;
        const galleryId = raw ? parseInt(raw, 10) : null;
        if (Number.isFinite(galleryId) && galleryId > 0) {
            jsonrpc("/wiki/gallery/purge", {gallery_id: galleryId}).catch(() => {});
        }
        this._super(...arguments);
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
    WikiGallery: options.registry.WikiGallery,
};
