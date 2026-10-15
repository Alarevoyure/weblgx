/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PageSearchModel } from "@website/components/views/page_search_model";

/**
 * Strict per-website isolation for events in the Website > Events backend list.
 */
patch(PageSearchModel.prototype, {
    async notifyWebsiteChange(websiteId) {
        await super.notifyWebsiteChange(...arguments);
        if (this.resModel === "event.event" && websiteId) {
            this.pagesState.websiteDomain = [["website_id", "=", websiteId]];
            this._notify();
        }
    },
});
