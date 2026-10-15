/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import animations from "@website/js/content/snippets.animation";

/**
 * Effets de défilement du Header Wiki (indépendants du Header site).
 * Modes : standard | scroll | fixed | disappears | fade-out
 */
publicWidget.registry.WikiHeaderScroll = animations.Animation.extend({
    selector: "#o_wiki_header",
    disabledInEditableMode: false,
    effects: [
        {
            startEvents: "scroll",
            update: "_updateOnScroll",
        },
        {
            startEvents: "resize",
            update: "_updateOnResize",
        },
    ],

    /**
     * @override
     */
    start() {
        this.effect =
            this.el.dataset.wikiScrollEffect ||
            this._effectFromClass() ||
            "standard";
        this.fixedHeader = false;
        this.headerIsScrolled = false;
        this.hasScrolled = false;
        this.fixedHeaderShow = false;
        this.scrolledPoint = this.effect === "standard" ? 300 : 0;
        this.scrollingDownwards = true;
        this.hiddenHeader = false;
        this.position = 0;
        this.atTop = true;
        this.checkPoint = 0;
        this.scrollOffsetLimit = 200;
        this.spacerEl = null;
        this.scrollableEl = $().getScrollingElement()[0];

        if (this.effect === "scroll") {
            return this._super(...arguments);
        }
        return this._super(...arguments);
    },

    /**
     * @override
     */
    destroy() {
        this._setAffixed(false);
        this.el.classList.remove(
            "o_wiki_header_is_scrolled",
            "o_wiki_header_no_transition"
        );
        this.el.style.transform = "";
        this.el.style.opacity = "";
        this.el.style.display = "";
        this.el.style.top = "";
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _effectFromClass() {
        const match = [...this.el.classList]
            .find((c) => c.startsWith("o_wiki_header_effect_"));
        return match ? match.replace("o_wiki_header_effect_", "") : null;
    },

    /**
     * Hauteur du header site (s'il est visible) pour caler le Wiki en dessous.
     *
     * @private
     */
    _computeTopGap() {
        const siteHeader = document.querySelector(
            "#wrapwrap > header:not(#o_wiki_header)"
        );
        if (!siteHeader) {
            return 0;
        }
        const style = window.getComputedStyle(siteHeader);
        if (style.display === "none" || style.visibility === "hidden") {
            return 0;
        }
        return siteHeader.getBoundingClientRect().height || 0;
    },

    /**
     * @private
     */
    _ensureSpacer() {
        if (this.spacerEl && this.spacerEl.isConnected) {
            return this.spacerEl;
        }
        this.spacerEl = document.createElement("div");
        this.spacerEl.className = "o_wiki_header_scroll_spacer";
        this.spacerEl.setAttribute("aria-hidden", "true");
        this.el.after(this.spacerEl);
        return this.spacerEl;
    },

    /**
     * @private
     * @param {boolean} useFixed
     */
    _setAffixed(useFixed) {
        this.fixedHeader = useFixed;
        this.el.classList.toggle("o_wiki_header_affixed", useFixed);
        const topGap = this._computeTopGap();
        if (useFixed) {
            const spacer = this._ensureSpacer();
            spacer.style.height = `${this.el.offsetHeight}px`;
            this.el.style.top = `${topGap}px`;
        } else if (this.spacerEl) {
            this.spacerEl.remove();
            this.spacerEl = null;
            this.el.style.top = "";
        }
    },

    /**
     * @private
     * @param {boolean} scrolled
     */
    _setScrolled(scrolled) {
        if (this.headerIsScrolled === scrolled) {
            return;
        }
        this.headerIsScrolled = scrolled;
        this.el.classList.toggle("o_wiki_header_is_scrolled", scrolled);
        if (this.spacerEl && this.fixedHeader) {
            // La hauteur peut changer (logo réduit).
            this.spacerEl.style.height = `${this.el.offsetHeight}px`;
        }
    },

    /**
     * @private
     */
    _showHeader() {
        this.el.style.opacity = "";
        this.el.style.display = "";
        this.el.style.pointerEvents = "";
        // Pas de translate(0,0) : un transform résiduel casse le 1er tap mobile.
        this.el.style.transform = "";
    },

    /**
     * @private
     */
    _hideHeader() {
        if (this.effect === "fade-out") {
            this.el.style.opacity = "0";
            this.el.style.pointerEvents = "none";
            return;
        }
        this.el.style.transform = "translate(0, -100%)";
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {number} scroll
     */
    _updateOnScroll(scroll) {
        if (this.effect === "scroll") {
            return;
        }

        if (!this.hasScrolled) {
            this.hasScrolled = true;
            if (scroll > 0) {
                this.el.classList.add("o_wiki_header_no_transition");
            }
        } else {
            this.el.classList.remove("o_wiki_header_no_transition");
        }

        const topGap = this._computeTopGap();
        this.el.style.top = this.fixedHeader ? `${topGap}px` : "";

        if (this.effect === "standard") {
            this._updateStandard(scroll, topGap);
            return;
        }
        if (this.effect === "fixed") {
            this._updateFixed(scroll, topGap);
            return;
        }
        // disappears | fade-out (basés sur fixed + hide/show)
        this._updateFixed(scroll, topGap);
        this._updateDisappearing(scroll, topGap);
    },

    /**
     * @private
     */
    _updateStandard(scroll, topGap) {
        const headerHeight = this.el.getBoundingClientRect().height;
        const mainPosScrolled = scroll > headerHeight + topGap;
        const reachPosScrolled =
            scroll > this.scrolledPoint + topGap;
        const fixedUpdate = this.fixedHeader !== mainPosScrolled;
        const showUpdate = this.fixedHeaderShow !== reachPosScrolled;

        if (fixedUpdate || showUpdate) {
            // transform uniquement pour masquer ; visible = pas de transform.
            this.el.style.transform =
                mainPosScrolled && !reachPosScrolled
                    ? "translate(0, -100%)"
                    : "";
            void this.el.offsetWidth;
        }

        this.fixedHeaderShow = reachPosScrolled;
        this._setScrolled(reachPosScrolled);

        if (fixedUpdate) {
            this._setAffixed(mainPosScrolled);
        }
    },

    /**
     * @private
     */
    _updateFixed(scroll, topGap) {
        if (scroll > this.scrolledPoint + topGap) {
            if (!this.fixedHeader) {
                this.el.style.transform = "";
                this._setAffixed(true);
            }
            this._setScrolled(true);
        } else {
            this._setAffixed(false);
            this._setScrolled(false);
            this.el.style.transform = "";
            this.el.style.opacity = "";
            this.el.style.pointerEvents = "";
            this.hiddenHeader = false;
        }
    },

    /**
     * @private
     */
    _updateDisappearing(scroll, topGap) {
        if (!this.fixedHeader) {
            return;
        }
        const scrollingDownwards = scroll > this.position;
        const atTop = scroll <= 0;
        if (scrollingDownwards !== this.scrollingDownwards) {
            this.checkPoint = scroll;
        }
        this.scrollingDownwards = scrollingDownwards;
        this.position = scroll;
        this.atTop = atTop;

        if (scrollingDownwards) {
            if (
                !this.hiddenHeader &&
                scroll - this.checkPoint > this.scrollOffsetLimit + topGap
            ) {
                this.hiddenHeader = true;
                this._hideHeader();
            }
        } else if (
            this.hiddenHeader &&
            scroll - this.checkPoint < -(this.scrollOffsetLimit + topGap) / 2
        ) {
            this.hiddenHeader = false;
            this._showHeader();
        }

        if (atTop) {
            this.hiddenHeader = false;
            this._showHeader();
        }
    },

    /**
     * @private
     */
    _updateOnResize() {
        if (!this.fixedHeader) {
            return;
        }
        const topGap = this._computeTopGap();
        this.el.style.top = `${topGap}px`;
        if (this.spacerEl) {
            this.spacerEl.style.height = `${this.el.offsetHeight}px`;
        }
    },
});

export default publicWidget.registry.WikiHeaderScroll;
