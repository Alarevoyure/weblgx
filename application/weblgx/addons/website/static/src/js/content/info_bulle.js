/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Affiche le texte data-info-bulle au survol et au clic
 * pour les liens de style « Info Bulle ».
 */
publicWidget.registry.InfoBulle = publicWidget.Widget.extend({
    selector: "a.o_info_bulle",
    events: {
        mouseenter: "_onShow",
        mouseleave: "_onHide",
        focus: "_onShow",
        blur: "_onHide",
        click: "_onClick",
    },

    /**
     * @override
     */
    start() {
        this._pinned = false;
        this.el.setAttribute("role", "button");
        this.el.setAttribute("tabindex", "0");
        if (!this.el.getAttribute("href")) {
            this.el.setAttribute("href", "#");
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        if (this._onDocumentClick) {
            document.removeEventListener("click", this._onDocumentClick, true);
            this._onDocumentClick = null;
        }
        this._removeTooltip();
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getContent() {
        return (this.el.getAttribute("data-info-bulle") || "").trim();
    },
    _showTooltip() {
        const text = this._getContent();
        if (!text) {
            return;
        }
        if (!this._tooltipEl) {
            this._tooltipEl = document.createElement("div");
            this._tooltipEl.className = "o_info_bulle_tooltip";
            this._tooltipEl.setAttribute("role", "tooltip");
            document.body.appendChild(this._tooltipEl);
        }
        this._tooltipEl.textContent = text;
        this._tooltipEl.classList.add("o_visible");
        this._positionTooltip();
    },
    _removeTooltip() {
        if (this._tooltipEl) {
            this._tooltipEl.remove();
            this._tooltipEl = null;
        }
    },
    _positionTooltip() {
        if (!this._tooltipEl) {
            return;
        }
        const rect = this.el.getBoundingClientRect();
        const tip = this._tooltipEl;
        const tipRect = tip.getBoundingClientRect();
        let top = window.scrollY + rect.top - tipRect.height - 8;
        let left = window.scrollX + rect.left + (rect.width - tipRect.width) / 2;
        if (top < window.scrollY + 4) {
            top = window.scrollY + rect.bottom + 8;
        }
        left = Math.max(8, Math.min(left, window.scrollX + window.innerWidth - tipRect.width - 8));
        tip.style.top = `${top}px`;
        tip.style.left = `${left}px`;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._pinned = !this._pinned;
        if (this._pinned) {
            this._showTooltip();
            // Ferme l'info-bulle au clic extérieur.
            this._onDocumentClick = (event) => {
                if (!this.el.contains(event.target) &&
                    !(this._tooltipEl && this._tooltipEl.contains(event.target))) {
                    this._pinned = false;
                    this._removeTooltip();
                    document.removeEventListener("click", this._onDocumentClick, true);
                    this._onDocumentClick = null;
                }
            };
            // Différé pour ne pas fermer immédiatement via le même clic.
            setTimeout(() => {
                document.addEventListener("click", this._onDocumentClick, true);
            }, 0);
        } else {
            if (this._onDocumentClick) {
                document.removeEventListener("click", this._onDocumentClick, true);
                this._onDocumentClick = null;
            }
            this._removeTooltip();
        }
    },
    _onShow() {
        this._showTooltip();
    },
    _onHide() {
        if (!this._pinned) {
            this._removeTooltip();
        }
    },
});
