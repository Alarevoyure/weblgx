/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * Building block : affiche le sommaire du wiki du site courant.
 */
const WikiTocSnippet = publicWidget.Widget.extend({
    selector: ".s_wiki_toc",
    disabledInEditableMode: false,
    events: {
        "click .o_wiki_toc_branch_toggle": "_onTocBranchToggle",
    },

    /**
     * @override
     */
    async start() {
        const proms = [this._super(...arguments)];
        proms.push(this._loadToc());
        return Promise.all(proms);
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    async _loadToc() {
        const tree = this.el.querySelector("[data-wiki-toc-target]");
        if (!tree) {
            return;
        }
        try {
            const res = await jsonrpc("/wiki/api/toc", {});
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            if (res && res.border_color) {
                this.el.style.setProperty("--wiki-border-color", res.border_color);
            }
            tree.innerHTML = (res && res.html) || "<p class=\"text-muted mb-0\">Aucune page wiki.</p>";
            this._initTocBranches();
            this.options.wysiwyg?.odooEditor?.observerActive?.();
        } catch {
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            tree.innerHTML = "<p class=\"text-muted mb-0\">Sommaire indisponible.</p>";
            this.options.wysiwyg?.odooEditor?.observerActive?.();
        }
    },

    _initTocBranches() {
        const branches = [...this.el.querySelectorAll(".o_wiki_toc_branch")];
        if (!branches.length) {
            return;
        }
        // Sur une page web hors /wiki : ouvrir la première branche par défaut.
        branches.forEach((branch, index) => {
            this._setTocBranchOpen(branch, index === 0);
        });
    },

    _setTocBranchOpen(branch, open) {
        branch.classList.toggle("is-open", !!open);
        const btn = branch.querySelector(".o_wiki_toc_branch_toggle");
        if (btn) {
            btn.setAttribute("aria-expanded", open ? "true" : "false");
        }
    },

    _onTocBranchToggle(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const branch = ev.currentTarget.closest(".o_wiki_toc_branch");
        if (!branch) {
            return;
        }
        const willOpen = !branch.classList.contains("is-open");
        if (willOpen) {
            this.el.querySelectorAll(".o_wiki_toc_branch.is-open").forEach((other) => {
                if (other !== branch) {
                    this._setTocBranchOpen(other, false);
                }
            });
        }
        this._setTocBranchOpen(branch, willOpen);
    },
});

publicWidget.registry.WikiTocSnippet = WikiTocSnippet;

export default WikiTocSnippet;
