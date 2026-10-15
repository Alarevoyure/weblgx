/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Ouvre / ferme le menu sandwich Wiki de façon fiable,
 * même quand le Header Wiki est affixed (évite le double-tap mobile).
 */
publicWidget.registry.WikiHeaderMobileToggle = publicWidget.Widget.extend({
    selector: "#o_wiki_header",
    events: {
        "click .o_wiki_header_toggler": "_onToggleClick",
    },

    /**
     * @private
     */
    _getOffcanvasEl() {
        return document.getElementById("o_wiki_header_offcanvas");
    },

    /**
     * @private
     */
    _ensureOnBody(offcanvasEl) {
        if (offcanvasEl && offcanvasEl.parentElement !== document.body) {
            document.body.appendChild(offcanvasEl);
        }
    },

    /**
     * @private
     */
    _onToggleClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const offcanvasEl = this._getOffcanvasEl();
        if (!offcanvasEl || typeof Offcanvas === "undefined") {
            return;
        }
        this._ensureOnBody(offcanvasEl);
        // Évite le bug mobile « premier tap perdu » sur un parent avec transform.
        this.el.style.transform = "";
        const instance = Offcanvas.getOrCreateInstance(offcanvasEl);
        if (offcanvasEl.classList.contains("show")) {
            instance.hide();
        } else {
            instance.show();
        }
    },
});

/**
 * Interactions dans le panneau sandwich (sommaire, fermeture au clic lien).
 */
publicWidget.registry.WikiHeaderMobile = publicWidget.Widget.extend({
    selector: "#o_wiki_header_offcanvas",
    events: {
        "click .o_wiki_toc_branch_toggle": "_onBranchToggle",
        "click a.o_wiki_toc_link": "_onNavLinkClick",
    },

    /**
     * @override
     */
    start() {
        this._super(...arguments);
        if (this.el.parentElement !== document.body) {
            document.body.appendChild(this.el);
        }
        this._initBranches();
        return Promise.resolve();
    },

    /**
     * @private
     */
    _initBranches() {
        const toc = this.el.querySelector("#o_wiki_header_mobile_toc");
        if (!toc) {
            return;
        }
        const branches = [...toc.querySelectorAll(".o_wiki_toc_branch")];
        if (!branches.length) {
            return;
        }
        let activeBranch = branches.find((branch) =>
            [...branch.querySelectorAll("a.o_wiki_toc_link")].some((a) =>
                a.classList.contains("selected")
            )
        );
        if (!activeBranch) {
            activeBranch = branches[0];
        }
        branches.forEach((branch) => {
            this._setBranchOpen(branch, branch === activeBranch);
        });
    },

    /**
     * @private
     */
    _setBranchOpen(branch, open) {
        branch.classList.toggle("is-open", !!open);
        const btn = branch.querySelector(".o_wiki_toc_branch_toggle");
        if (btn) {
            btn.setAttribute("aria-expanded", open ? "true" : "false");
        }
    },

    /**
     * @private
     */
    _closeOffcanvas() {
        if (typeof Offcanvas === "undefined") {
            return;
        }
        Offcanvas.getOrCreateInstance(this.el).hide();
    },

    /**
     * @private
     */
    _onBranchToggle(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const branch = ev.currentTarget.closest(".o_wiki_toc_branch");
        if (!branch) {
            return;
        }
        const willOpen = !branch.classList.contains("is-open");
        if (willOpen) {
            const toc = this.el.querySelector("#o_wiki_header_mobile_toc");
            toc?.querySelectorAll(".o_wiki_toc_branch.is-open").forEach((other) => {
                if (other !== branch) {
                    this._setBranchOpen(other, false);
                }
            });
        }
        this._setBranchOpen(branch, willOpen);
    },

    /**
     * @private
     */
    _onNavLinkClick() {
        this._closeOffcanvas();
    },
});

export default {
    WikiHeaderMobileToggle: publicWidget.registry.WikiHeaderMobileToggle,
    WikiHeaderMobile: publicWidget.registry.WikiHeaderMobile,
};
