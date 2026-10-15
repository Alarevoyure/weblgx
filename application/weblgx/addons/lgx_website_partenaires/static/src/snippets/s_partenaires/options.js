/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

const MAX_LOGOS = 20;
const MIN_LOGOS = 1;
const ORIGINAL_ITEM = ".s_partenaires_item:not(.s_partenaires_clone)";

options.registry.Partenaires = options.registry.MultipleItems.extend({
    /**
     * Strip runtime clones so they are never persisted in the page HTML.
     *
     * @override
     */
    cleanForSave() {
        this._copyLinksFromClones();
        this._removeClones();
    },

    /**
     * @override
     */
    async addItem(previewMode, widgetValue, params) {
        const count = this._getLogoCount();
        if (count >= MAX_LOGOS) {
            return;
        }
        this._removeClones();
        params = Object.assign({}, params, {
            item: `${ORIGINAL_ITEM}:last`,
        });
        await this._super(previewMode, widgetValue, params);
        this._notifyCarouselRefresh();
    },

    /**
     * @override
     */
    async removeItem(previewMode, widgetValue, params) {
        const count = this._getLogoCount();
        if (count <= MIN_LOGOS) {
            return;
        }
        this._removeClones();
        params = Object.assign({}, params, {
            item: `${ORIGINAL_ITEM}:last`,
        });
        await this._super(previewMode, widgetValue, params);
        this._notifyCarouselRefresh();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {number}
     */
    _getLogoCount() {
        return this.$target.find(ORIGINAL_ITEM).length;
    },

    /**
     * Si un lien a été posé sur une copie visible pendant le défilement,
     * le reporter sur le logo réel avant de supprimer les copies.
     *
     * @private
     */
    _copyLinksFromClones() {
        const originals = [...this.$target[0].querySelectorAll(ORIGINAL_ITEM)];
        this.$target[0].querySelectorAll(".s_partenaires_clone").forEach((clone) => {
            const index = parseInt(clone.dataset.cloneIndex, 10);
            const original = originals[index];
            if (!original || original.querySelector("a[href]")) {
                return;
            }
            if (clone.querySelector("a[href]")) {
                original.innerHTML = clone.innerHTML;
            }
        });
    },

    /**
     * @private
     */
    _removeClones() {
        this.$target.find(".s_partenaires_clone").remove();
        const track = this.$target.find(".s_partenaires_track")[0];
        if (track) {
            track.style.transform = "";
            track.classList.remove("s_partenaires_no_transition");
        }
    },

    /**
     * @private
     */
    _notifyCarouselRefresh() {
        // Restart public widget so the track/controls stay in sync after edits.
        this.trigger_up("widgets_start_request", {
            $target: this.$target,
            editableMode: true,
        });
    },

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        const count = this._getLogoCount();
        if (widgetName === "add_logo_opt") {
            return count < MAX_LOGOS;
        }
        if (widgetName === "remove_logo_opt") {
            return count > MIN_LOGOS;
        }
        return this._super(...arguments);
    },
});

export default {
    Partenaires: options.registry.Partenaires,
};
