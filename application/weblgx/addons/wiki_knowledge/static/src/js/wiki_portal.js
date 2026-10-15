/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";

publicWidget.registry.wikiPortal = publicWidget.Widget.extend({
    selector: "#o_wiki_root",
    events: {
        "click #o_wiki_btn_edit_content": "_onEditContent",
        "click #o_wiki_btn_save_content": "_onSaveContent",
        "click #o_wiki_btn_cancel_content": "_onCancelContent",
        "click .o_wiki_toc_toggle": "_onTocToggleClick",
        "click .o_wiki_toc_backdrop": "_onTocBackdropClick",
        "click .o_wiki_toc_close": "_onTocCloseClick",
        "click .o_wiki_toc_branch_toggle": "_onTocBranchToggle",
        "click .o_wiki_page_nav_link": "_onPageNavClick",
        "click .o_wiki_article_zoom": "_onArticleZoom",
        "click .o_wiki_article_lightbox": "_onArticleZoomClose",
        "click .o_wiki_article_lightbox_close": "_onArticleZoomClose",
    },

    start() {
        this._super(...arguments);
        this.wysiwyg = null;
        this.originalContent = "";
        this.canFrontEdit = this.el.dataset.canFrontEdit === "1";
        this.pageState = this.el.dataset.pageState || "";
        this.showPageNav = this.el.dataset.showPageNav === "1";
        this._onWindowClickCaptureBound = this._onWindowClickCapture.bind(this);
        window.addEventListener("click", this._onWindowClickCaptureBound, true);
        this._onResizeBound = this._onResize.bind(this);
        this._onKeydownBound = this._onKeydown.bind(this);
        window.addEventListener("resize", this._onResizeBound);
        window.addEventListener("keydown", this._onKeydownBound);
        this._initTocBranches();
        if (this.showPageNav) {
            this._buildPageNav();
        }
        return Promise.resolve();
    },

    destroy() {
        window.removeEventListener("click", this._onWindowClickCaptureBound, true);
        window.removeEventListener("resize", this._onResizeBound);
        window.removeEventListener("keydown", this._onKeydownBound);
        this._setTocOpen(false);
        if (this.wysiwyg) {
            this.wysiwyg.destroy();
            this.wysiwyg = null;
        }
        return this._super(...arguments);
    },

    // -------------------------------------------------------------------------
    // Utils
    // -------------------------------------------------------------------------

    getCurrentPageId() {
        const hid = this.el.querySelector("#o_wiki_current_page_id");
        return hid && hid.value ? Number(hid.value) : null;
    },

    _isMobileTocLayout() {
        return window.matchMedia("(max-width: 991.98px)").matches;
    },

    _buildPageNav() {
        // Navigation de page uniquement sur les écrans larges.
        if (this._isMobileTocLayout()) {
            return;
        }
        const nav = this.el.querySelector("#o_wiki_page_nav_list");
        const editorArea = this.el.querySelector("#o_wiki_editor_area");
        if (!nav || !editorArea) {
            return;
        }
        nav.innerHTML = "";
        const headings = [...editorArea.querySelectorAll("h1, h2, h3, h4")].filter(
            (h) => (h.textContent || "").trim()
        );
        if (headings.length <= 1) {
            this.el.classList.add("o_wiki_page_nav_empty");
            return;
        }
        this.el.classList.remove("o_wiki_page_nav_empty");
        const seenIds = new Set();

        const slugify = (text) => {
            const base = (text || "")
                .toString()
                .trim()
                .toLowerCase()
                .replace(/[\s]+/g, "-")
                .replace(/[^a-z0-9\-]/g, "")
                .slice(0, 50) || "section";
            let candidate = base;
            let idx = 1;
            while (seenIds.has(candidate)) {
                candidate = `${base}-${idx++}`;
            }
            seenIds.add(candidate);
            return candidate;
        };

        headings.forEach((h, index) => {
            const level = parseInt(h.tagName.slice(1), 10) || 2;
            const text = (h.textContent || "").trim();
            if (!h.id) {
                h.id = slugify(text) + "-" + index;
            } else {
                seenIds.add(h.id);
            }
            const link = document.createElement("a");
            link.className = `o_wiki_page_nav_link o_wiki_page_nav_level-${level}`;
            link.href = `#${h.id}`;
            link.textContent = text;
            nav.appendChild(link);
        });
    },

    _setTocOpen(open) {
        if (open && !this._isMobileTocLayout()) {
            return;
        }
        const isOpen = !!open;
        this.el.classList.toggle("o_wiki_toc_open", isOpen);
        document.body.classList.toggle("o_wiki_toc_open", isOpen);
        const btn = this.el.querySelector(".o_wiki_toc_toggle");
        if (btn) {
            btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
        }
    },

    _onTocToggleClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (!this._isMobileTocLayout()) {
            return;
        }
        this._setTocOpen(!this.el.classList.contains("o_wiki_toc_open"));
    },

    _onTocBackdropClick(ev) {
        ev.preventDefault();
        this._setTocOpen(false);
    },

    _onTocCloseClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._setTocOpen(false);
    },

    _onResize() {
        if (!this._isMobileTocLayout()) {
            this._setTocOpen(false);
        }
    },

    _onKeydown(ev) {
        if (ev.key !== "Escape") {
            return;
        }
        const lightbox = this.el.querySelector(".o_wiki_article_lightbox");
        if (lightbox && !lightbox.hidden) {
            this._setArticleZoom(false);
            return;
        }
        if (this.el.classList.contains("o_wiki_toc_open")) {
            this._setTocOpen(false);
        }
    },

    _onArticleZoom(ev) {
        ev.preventDefault();
        this._setArticleZoom(true);
    },

    _onArticleZoomClose(ev) {
        ev.preventDefault();
        this._setArticleZoom(false);
    },

    _setArticleZoom(open) {
        const lightbox = this.el.querySelector(".o_wiki_article_lightbox");
        if (!lightbox) {
            return;
        }
        lightbox.hidden = !open;
        document.body.classList.toggle("o_wiki_article_zoom_open", open);
    },

    _onPageNavClick(ev) {
        const link = ev.currentTarget;
        if (!link || !link.getAttribute) {
            return;
        }
        const href = link.getAttribute("href") || "";
        if (!href.startsWith("#")) {
            return;
        }
        const targetId = href.slice(1);
        const editorArea = this.el.querySelector("#o_wiki_editor_area");
        if (!editorArea) {
            return;
        }
        const target = editorArea.querySelector(`#${CSS.escape(targetId)}`);
        if (!target) {
            return;
        }
        ev.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
    },

    _initTocBranches() {
        const branches = [...this.el.querySelectorAll(".o_wiki_toc_branch")];
        if (!branches.length) {
            return;
        }
        const currentId = String(this.getCurrentPageId() || "");
        let activeBranch = branches.find((branch) =>
            [...branch.querySelectorAll("a.o_wiki_toc_link")].some(
                (link) => link.dataset.id === currentId
            )
        );
        if (!activeBranch) {
            activeBranch = branches[0];
        }
        branches.forEach((branch) => {
            this._setTocBranchOpen(branch, branch === activeBranch);
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

    _setEditMode(editMode) {
        const editorArea = this.el.querySelector("#o_wiki_editor_area");
        const wrap = this.el.querySelector("#o_wiki_wysiwyg_wrap");
        const btnEdit = this.el.querySelector("#o_wiki_btn_edit_content");
        const btnSave = this.el.querySelector("#o_wiki_btn_save_content");
        const btnCancel = this.el.querySelector("#o_wiki_btn_cancel_content");
        if (editorArea) {
            editorArea.classList.toggle("d-none", editMode);
        }
        if (wrap) {
            wrap.classList.toggle("d-none", !editMode);
        }
        if (btnEdit) {
            btnEdit.classList.toggle("d-none", editMode);
        }
        if (btnSave) {
            btnSave.classList.toggle("d-none", !editMode);
        }
        if (btnCancel) {
            btnCancel.classList.toggle("d-none", !editMode);
        }
    },

    async _onEditContent(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.pageState === "to_review") {
            alert("Page en validation: edition verrouillee.");
            return;
        }
        if (!this.canFrontEdit || this.wysiwyg) {
            return;
        }
        const editorArea = this.el.querySelector("#o_wiki_editor_area");
        const textarea = this.el.querySelector("#o_wiki_content_textarea");
        if (!editorArea || !textarea) {
            return;
        }
        // Retire l'éditeur de la bibliothèque avant la copie, sinon il est
        // enregistré dans la page et réapparaît en double au prochain affichage.
        document.dispatchEvent(new CustomEvent("wiki-gallery-canonicalize"));
        this.originalContent = editorArea.innerHTML || "";
        textarea.value = this.originalContent;
        this._setEditMode(true);
        try {
            this.wysiwyg = await loadWysiwygFromTextarea(this, textarea, {
                value: textarea.value,
                styleInline: true,
                codeview: !!odoo.debug,
                resizable: false,
                allowCommandImage: true,
                allowCommandVideo: false,
                toolbarOptions: {
                    showLink: true,
                    showImageEdit: true,
                    showImageWidth: true,
                    showHistory: true,
                    showFontSize: true,
                },
                recordInfo: {
                    res_model: "wiki.page",
                    res_id: this.getCurrentPageId() || 0,
                },
            });
        } catch {
            this._teardownEditor();
            alert("Impossible de charger l'editeur.");
        }
    },

    _teardownEditor() {
        if (this.wysiwyg) {
            this.wysiwyg.destroy();
            this.wysiwyg = null;
        }
        this._setEditMode(false);
    },

    async _onSaveContent(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const pageId = this.getCurrentPageId();
        if (!pageId) {
            return;
        }
        const editorArea = this.el.querySelector("#o_wiki_editor_area");
        const content = this.wysiwyg ? (this.wysiwyg.getValue() || "") : (editorArea ? (editorArea.innerHTML || "") : "");
        const res = await jsonrpc(`/wiki/api/page/${pageId}/save`, { content });
        if (res && res.error) {
            if (res.error === "locked_for_review") {
                alert("Page en validation: enregistrement bloque.");
            } else {
                alert(res.error);
            }
            return;
        }
        if (editorArea) {
            editorArea.innerHTML = content;
        }
        this._teardownEditor();
        document.dispatchEvent(new CustomEvent("wiki-gallery-canonicalize", {
            detail: {reinit: true},
        }));
    },

    async _onCancelContent(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.wysiwyg?.odooEditor?.editable) {
            this.wysiwyg.odooEditor.editable.innerHTML = this.originalContent || "";
        }
        this._teardownEditor();
        document.dispatchEvent(new CustomEvent("wiki-gallery-canonicalize", {
            detail: {reinit: true},
        }));
    },

    _onWindowClickCapture(ev) {
        const tocLink = ev.target.closest("#o_wiki_toc_tree a.o_wiki_toc_link");
        if (!tocLink || !this.el.contains(tocLink)) {
            return;
        }
        if (ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.button !== 0) {
            return;
        }
        const targetUrl = tocLink.getAttribute("href");
        if (!targetUrl || targetUrl === "#") {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        if (this._isMobileTocLayout()) {
            this._setTocOpen(false);
        }
        window.location.assign(targetUrl);
    },
});
