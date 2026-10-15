/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

const WIKI_HEADER_ELEMENT_FIELDS = {
    wikiHeaderShowLogo: "wiki_header_show_logo",
    wikiHeaderShowSearch: "wiki_header_show_search",
    wikiHeaderShowSignin: "wiki_header_show_signin",
    wikiHeaderShowMenu: "wiki_header_show_menu",
};

/**
 * Case à cocher « Afficher sur le Wiki » (header du site / Header Wiki).
 * Persiste website.wiki_show_site_header (isolé multi-site).
 */
options.registry.WikiShowSiteHeader = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiShowSiteHeader(previewMode, widgetValue, params) {
        if (previewMode) {
            return;
        }
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return;
        }
        const checked = widgetValue === "true" || widgetValue === true;
        await this.orm.write("website", [websiteId], {
            wiki_show_site_header: checked,
        });
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === "wikiShowSiteHeader") {
            const websiteId = this._getWebsiteId();
            if (!websiteId) {
                return "true";
            }
            const rows = await this.orm.read(
                "website",
                [websiteId],
                ["wiki_show_site_header"]
            );
            return rows[0]?.wiki_show_site_header ? "true" : "";
        }
        return this._super(...arguments);
    },

    /**
     * @private
     * @returns {number|false}
     */
    _getWebsiteId() {
        let websiteId = false;
        this.trigger_up("context_get", {
            callback: (ctx) => {
                websiteId = ctx.website_id;
            },
        });
        return websiteId;
    },
});

/**
 * Boutons « Éléments » du Header Wiki : Logo, Recherche, Inscription.
 */
options.registry.WikiHeaderElements = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiHeaderShowLogo(previewMode, widgetValue, params) {
        if (previewMode) {
            return;
        }
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return;
        }
        const checked = widgetValue === "true" || widgetValue === true;
        const vals = { wiki_header_show_logo: checked };
        if (checked) {
            vals.wiki_header_brand_type = "image";
        }
        await this.orm.write("website", [websiteId], vals);
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiHeaderShowSearch(previewMode, widgetValue, params) {
        return this._setElementFlag(previewMode, "wiki_header_show_search", widgetValue);
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiHeaderShowSignin(previewMode, widgetValue, params) {
        return this._setElementFlag(previewMode, "wiki_header_show_signin", widgetValue);
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiHeaderShowMenu(previewMode, widgetValue, params) {
        return this._setElementFlag(previewMode, "wiki_header_show_menu", widgetValue);
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const field = WIKI_HEADER_ELEMENT_FIELDS[methodName];
        if (field) {
            const websiteId = this._getWebsiteId();
            if (!websiteId) {
                return "";
            }
            const rows = await this.orm.read("website", [websiteId], [field]);
            return rows[0]?.[field] ? "true" : "";
        }
        return this._super(...arguments);
    },

    /**
     * @private
     */
    async _setElementFlag(previewMode, field, widgetValue) {
        if (previewMode) {
            return;
        }
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return;
        }
        const checked = widgetValue === "true" || widgetValue === true;
        await this.orm.write("website", [websiteId], {
            [field]: checked,
        });
    },

    /**
     * @private
     * @returns {number|false}
     */
    _getWebsiteId() {
        let websiteId = false;
        this.trigger_up("context_get", {
            callback: (ctx) => {
                websiteId = ctx.website_id;
            },
        });
        return websiteId;
    },
});

/**
 * Options « Logo Wiki » : type (None / Text / Image) + hauteur.
 * Isolé du logo / hauteur du Header site (multi-site SaaS).
 */
options.registry.WikiHeaderLogo = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiHeaderBrand(previewMode, widgetValue, params) {
        if (previewMode) {
            return;
        }
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return;
        }
        const mode = widgetValue || "none";
        if (mode === "none") {
            await this.orm.write("website", [websiteId], {
                wiki_header_show_logo: false,
            });
            return;
        }
        await this.orm.write("website", [websiteId], {
            wiki_header_show_logo: true,
            wiki_header_brand_type: mode,
        });
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiLogoHeight(previewMode, widgetValue, params) {
        const height = this._parseHeight(widgetValue);
        this._applyLogoHeight("--wiki-logo-height", height);
        if (previewMode === true || previewMode === "reset") {
            return;
        }
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return;
        }
        await this.orm.write("website", [websiteId], {
            wiki_logo_height: height,
        });
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiLogoHeightScrolled(previewMode, widgetValue, params) {
        const height = this._parseHeight(widgetValue);
        this._applyLogoHeight("--wiki-logo-height-scrolled", height);
        if (previewMode === true || previewMode === "reset") {
            return;
        }
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return;
        }
        await this.orm.write("website", [websiteId], {
            wiki_logo_height_scrolled: height,
        });
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return this._super(...arguments);
        }
        if (methodName === "wikiHeaderBrand") {
            const rows = await this.orm.read("website", [websiteId], [
                "wiki_header_show_logo",
                "wiki_header_brand_type",
            ]);
            const row = rows[0] || {};
            if (!row.wiki_header_show_logo) {
                return "none";
            }
            return row.wiki_header_brand_type || "image";
        }
        if (methodName === "wikiLogoHeight") {
            const rows = await this.orm.read("website", [websiteId], [
                "wiki_logo_height",
            ]);
            const height = rows[0]?.wiki_logo_height || 40;
            return `${height}px`;
        }
        if (methodName === "wikiLogoHeightScrolled") {
            const rows = await this.orm.read("website", [websiteId], [
                "wiki_logo_height_scrolled",
                "wiki_logo_height",
            ]);
            const height =
                rows[0]?.wiki_logo_height_scrolled ||
                rows[0]?.wiki_logo_height ||
                40;
            return `${height}px`;
        }
        return this._super(...arguments);
    },

    /**
     * @private
     */
    _parseHeight(widgetValue) {
        const raw = String(widgetValue || "")
            .replace(/px/gi, "")
            .trim();
        const height = parseInt(raw, 10);
        if (Number.isNaN(height) || height < 1) {
            return 40;
        }
        return Math.min(height, 400);
    },

    /**
     * @private
     */
    _applyLogoHeight(cssVar, height) {
        const header =
            this.$target.closest("#o_wiki_header")[0] ||
            this.$target[0]?.closest?.("#o_wiki_header");
        if (header) {
            header.style.setProperty(cssVar, `${height}px`);
        }
    },

    /**
     * @private
     * @returns {number|false}
     */
    _getWebsiteId() {
        let websiteId = false;
        this.trigger_up("context_get", {
            callback: (ctx) => {
                websiteId = ctx.website_id;
            },
        });
        return websiteId;
    },
});

/**
 * Effet de défilement du Header Wiki (isolé multi-site).
 */
options.registry.WikiHeaderScrollEffect = options.Class.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @see this.selectClass for parameters
     */
    async wikiHeaderScrollEffect(previewMode, widgetValue, params) {
        if (previewMode) {
            return;
        }
        const websiteId = this._getWebsiteId();
        if (!websiteId) {
            return;
        }
        const effect = widgetValue || "standard";
        await this.orm.write("website", [websiteId], {
            wiki_header_scroll_effect: effect,
        });
    },

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === "wikiHeaderScrollEffect") {
            const websiteId = this._getWebsiteId();
            if (!websiteId) {
                return "standard";
            }
            const rows = await this.orm.read("website", [websiteId], [
                "wiki_header_scroll_effect",
            ]);
            return rows[0]?.wiki_header_scroll_effect || "standard";
        }
        return this._super(...arguments);
    },

    /**
     * @private
     * @returns {number|false}
     */
    _getWebsiteId() {
        let websiteId = false;
        this.trigger_up("context_get", {
            callback: (ctx) => {
                websiteId = ctx.website_id;
            },
        });
        return websiteId;
    },
});

export default {
    WikiShowSiteHeader: options.registry.WikiShowSiteHeader,
    WikiHeaderElements: options.registry.WikiHeaderElements,
    WikiHeaderLogo: options.registry.WikiHeaderLogo,
    WikiHeaderScrollEffect: options.registry.WikiHeaderScrollEffect,
};
