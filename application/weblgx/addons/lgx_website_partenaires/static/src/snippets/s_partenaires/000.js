/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const VISIBLE_DESKTOP = 6;

const PartenairesCarousel = publicWidget.Widget.extend({
    selector: ".s_partenaires",
    disabledInEditableMode: false,
    events: {
        "click .s_partenaires_prev": "_onPrev",
        "click .s_partenaires_next": "_onNext",
    },

    /**
     * @override
     */
    start() {
        this.trackEl = this.el.querySelector(".s_partenaires_track");
        this.viewportEl = this.el.querySelector(".s_partenaires_viewport");
        this.prevBtn = this.el.querySelector(".s_partenaires_prev");
        this.nextBtn = this.el.querySelector(".s_partenaires_next");
        this.currentIndex = 0;
        this.realCount = 0;
        this._isJumping = false;
        this._onResize = this._onResize.bind(this);
        this._onMouseEnter = this._pause.bind(this);
        this._onMouseLeave = this._play.bind(this);
        this._onTransitionEnd = this._onTransitionEnd.bind(this);

        window.addEventListener("resize", this._onResize);
        this.el.addEventListener("mouseenter", this._onMouseEnter);
        this.el.addEventListener("mouseleave", this._onMouseLeave);
        if (this.trackEl) {
            this.trackEl.addEventListener("transitionend", this._onTransitionEnd);
        }

        this._refresh();
        if (!this.editableMode) {
            this._play();
        }
        return this._super(...arguments);
    },

    /**
     * @override
     */
    destroy() {
        this._pause();
        window.removeEventListener("resize", this._onResize);
        this.el.removeEventListener("mouseenter", this._onMouseEnter);
        this.el.removeEventListener("mouseleave", this._onMouseLeave);
        if (this.trackEl) {
            this.trackEl.removeEventListener("transitionend", this._onTransitionEnd);
            this._removeClones();
            this.trackEl.style.transform = "";
            this.trackEl.classList.remove("s_partenaires_no_transition");
        }
        this._clearItemSizes();
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {HTMLElement[]}
     */
    _getOriginalItems() {
        return [...this.el.querySelectorAll(".s_partenaires_item:not(.s_partenaires_clone)")];
    },

    /**
     * @private
     * @returns {HTMLElement[]}
     */
    _getAllItems() {
        return [...this.el.querySelectorAll(".s_partenaires_item")];
    },

    /**
     * @private
     * @returns {number}
     */
    _getVisibleCount() {
        const fromCss = parseInt(
            getComputedStyle(this.el).getPropertyValue("--partenaires-visible"),
            10
        );
        return Number.isFinite(fromCss) && fromCss > 0 ? fromCss : VISIBLE_DESKTOP;
    },

    /**
     * @private
     * @returns {boolean}
     */
    _needsScroll() {
        return this.realCount > this._getVisibleCount();
    },

    /**
     * @private
     * @returns {number}
     */
    _getInterval() {
        const raw = parseInt(this.el.dataset.interval, 10);
        return Number.isFinite(raw) && raw > 0 ? raw : 3000;
    },

    /**
     * @private
     * @returns {number}
     */
    _getItemWidth() {
        const items = this._getAllItems();
        if (!items.length) {
            return 0;
        }
        return items[0].getBoundingClientRect().width;
    },

    /**
     * Item width must be based on the viewport, not the track length,
     * otherwise clones would shrink every logo.
     *
     * @private
     */
    _applyItemSizes() {
        if (!this.viewportEl) {
            return;
        }
        const visible = this._getVisibleCount();
        const itemWidth = this.viewportEl.clientWidth / visible;
        this._getAllItems().forEach((item) => {
            item.style.flex = `0 0 ${itemWidth}px`;
            item.style.width = `${itemWidth}px`;
            item.style.maxWidth = `${itemWidth}px`;
        });
    },

    /**
     * @private
     */
    _clearItemSizes() {
        this._getAllItems().forEach((item) => {
            item.style.flex = "";
            item.style.width = "";
            item.style.maxWidth = "";
        });
    },

    /**
     * @private
     */
    _removeClones() {
        this.el.querySelectorAll(".s_partenaires_clone").forEach((el) => el.remove());
    },

    /**
     * Duplicate the original logos after (and before) the real set so the
     * track can slide continuously without rewinding.
     *
     * @private
     */
    _setupClones() {
        this._removeClones();
        const originals = this._getOriginalItems();
        this.realCount = originals.length;

        if (!this._needsScroll() || !this.trackEl) {
            return;
        }

        // Append a full copy for seamless forward scrolling.
        originals.forEach((item, index) => {
            this.trackEl.appendChild(this._buildClone(item, index));
        });

        // Prepend a full copy for seamless backward scrolling.
        // Insert in reverse order so the visual sequence stays correct.
        for (let i = originals.length - 1; i >= 0; i--) {
            this.trackEl.insertBefore(
                this._buildClone(originals[i], i),
                this.trackEl.firstChild
            );
        }

        // Start on the middle (real) set.
        this.currentIndex = this.realCount;
        this._jumpTo(this.currentIndex);
    },

    /**
     * @private
     * @param {HTMLElement} item
     * @param {number} index
     * @returns {HTMLElement}
     */
    _buildClone(item, index) {
        const clone = item.cloneNode(true);
        clone.classList.add("s_partenaires_clone", "o_not_editable");
        clone.dataset.cloneIndex = String(index);
        clone.setAttribute("aria-hidden", "true");
        clone.removeAttribute("contenteditable");
        clone.querySelectorAll("[contenteditable]").forEach((el) => {
            el.removeAttribute("contenteditable");
        });
        this._muteCloneInteractions(clone);
        return clone;
    },

    /**
     * Les copies ne prennent pas le focus clavier, mais leur lien reste cliquable.
     *
     * @private
     * @param {HTMLElement} clone
     */
    _muteCloneInteractions(clone) {
        clone.querySelectorAll("a, button, input, select, textarea, [tabindex]").forEach((el) => {
            el.setAttribute("tabindex", "-1");
        });
    },

    /**
     * Recopie le HTML réel (donc le lien) sur les copies avant un défilement.
     *
     * @private
     */
    _syncClonesFromOriginals() {
        if (this.editableMode || !this.trackEl) {
            return;
        }
        this._getOriginalItems().forEach((item, index) => {
            const html = item.innerHTML;
            this.trackEl
                .querySelectorAll(`.s_partenaires_clone[data-clone-index="${index}"]`)
                .forEach((clone) => {
                    if (clone.innerHTML !== html) {
                        clone.innerHTML = html;
                        this._muteCloneInteractions(clone);
                    }
                });
        });
    },

    /**
     * @private
     */
    _refresh() {
        // Preserve relative position when possible (e.g. after resize).
        const previousReal = this.realCount;
        const offsetInReal =
            previousReal > 0 ? ((this.currentIndex % previousReal) + previousReal) % previousReal : 0;

        this.realCount = this._getOriginalItems().length;
        this.el.classList.toggle("s_partenaires_no_scroll", !this._needsScroll());

        // En édition, pas de copies : le lien doit rester sur le logo réel,
        // sinon il disparaît au défilement ou à l'enregistrement.
        if (this._needsScroll() && !this.editableMode) {
            this._setupClones();
            this.currentIndex = this.realCount + offsetInReal;
            this._applyItemSizes();
            this._jumpTo(this.currentIndex);
        } else {
            this._removeClones();
            const maxIndex = Math.max(0, this.realCount - this._getVisibleCount());
            this.currentIndex = Math.min(offsetInReal, maxIndex);
            this._applyItemSizes();
            this._jumpTo(this.currentIndex);
        }

        this._updateControls();

        if (!this.editableMode) {
            if (!this._needsScroll()) {
                this._pause();
            } else if (!this._timer) {
                this._play();
            }
        }
    },

    /**
     * Instantly place the track without animation.
     *
     * @private
     * @param {number} index
     */
    _jumpTo(index) {
        if (!this.trackEl) {
            return;
        }
        this._isJumping = true;
        this.trackEl.classList.add("s_partenaires_no_transition");
        this.currentIndex = index;
        this._updateTransform();
        // Force reflow so the next animated move starts from the jumped position.
        void this.trackEl.offsetWidth;
        this.trackEl.classList.remove("s_partenaires_no_transition");
        this._isJumping = false;
    },

    /**
     * @private
     */
    _updateTransform() {
        if (!this.trackEl) {
            return;
        }
        const itemWidth = this._getItemWidth();
        this.trackEl.style.transform = `translateX(-${this.currentIndex * itemWidth}px)`;
    },

    /**
     * @private
     */
    _updateControls() {
        const hide = !this._needsScroll();
        if (this.prevBtn) {
            this.prevBtn.disabled = hide;
            this.prevBtn.classList.toggle("o_hidden", hide);
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = hide;
            this.nextBtn.classList.toggle("o_hidden", hide);
        }
    },

    /**
     * After a slide into a cloned set, silently recenter on the real set.
     *
     * @private
     * @param {TransitionEvent} ev
     */
    _onTransitionEnd(ev) {
        if (ev.target !== this.trackEl || ev.propertyName !== "transform") {
            return;
        }
        if (!this._needsScroll() || this._isJumping || this.editableMode) {
            return;
        }
        if (!this.el.querySelector(".s_partenaires_clone")) {
            return;
        }
        // [clones][real][clones] → indexes: 0..n-1 | n..2n-1 | 2n..3n-1
        if (this.currentIndex >= this.realCount * 2) {
            this._jumpTo(this.currentIndex - this.realCount);
        } else if (this.currentIndex < this.realCount) {
            this._jumpTo(this.currentIndex + this.realCount);
        }
    },

    /**
     * @private
     * @param {number} delta
     */
    _go(delta) {
        if (!this._needsScroll() || this._isJumping) {
            return;
        }
        if (this.editableMode || !this.el.querySelector(".s_partenaires_clone")) {
            const maxIndex = Math.max(0, this.realCount - this._getVisibleCount());
            this.currentIndex = Math.min(maxIndex, Math.max(0, this.currentIndex + delta));
            this._updateTransform();
            this._updateControls();
            return;
        }
        this._syncClonesFromOriginals();
        this.currentIndex += delta;
        this._updateTransform();
        this._updateControls();
    },

    /**
     * @private
     */
    _play() {
        this._pause();
        if (this.editableMode || !this._needsScroll()) {
            return;
        }
        this._timer = setInterval(() => this._go(1), this._getInterval());
    },

    /**
     * @private
     */
    _pause() {
        if (this._timer) {
            clearInterval(this._timer);
            this._timer = null;
        }
    },

    /**
     * @private
     */
    _onResize() {
        this._refresh();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onPrev(ev) {
        ev.preventDefault();
        this._go(-1);
        if (!this.editableMode) {
            this._play();
        }
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onNext(ev) {
        ev.preventDefault();
        this._go(1);
        if (!this.editableMode) {
            this._play();
        }
    },
});

publicWidget.registry.PartenairesCarousel = PartenairesCarousel;

export default PartenairesCarousel;
