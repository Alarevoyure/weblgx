/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const MAX_AUDIO_BYTES = 20 * 1024 * 1024;
const MAX_VIDEO_BYTES = 50 * 1024 * 1024;

/**
 * Building block : bibliothèque d'images Wiki (dépôt public + tuiles validées).
 */
const WikiGallerySnippet = publicWidget.Widget.extend({
    selector: ".s_wiki_gallery",
    disabledInEditableMode: false,
    events: {
        "submit .s_wiki_gallery_form": "_onSubmit",
        "click .s_wiki_gallery_tile": "_onTileClick",
        "keydown .s_wiki_gallery_tile": "_onTileKeydown",
        "click .s_wiki_gallery_toggle": "_onToggleContribution",
        "click .s_wiki_gallery_verify_confirm": "_onVerifyConfirm",
        "click .s_wiki_gallery_verify_cancel": "_onVerifyCancel",
        "keydown .s_wiki_gallery_verify_code": "_onVerifyCodeKeydown",
    },

    /**
     * @override
     */
    async start() {
        this._itemsById = {};
        this._onModalKeydown = this._onModalKeydown.bind(this);
        this._onCanonicalize = this._onCanonicalize.bind(this);
        document.addEventListener("wiki-gallery-canonicalize", this._onCanonicalize);
        this._ensureRequiredFields();
        this._prepareContributionToggle();
        const proms = [this._super(...arguments)];
        proms.push(this._loadGallery());
        return Promise.all(proms);
    },

    /**
     * @override
     */
    destroy() {
        document.removeEventListener("wiki-gallery-canonicalize", this._onCanonicalize);
        this._closeArticle();
        if (this._galleryWysiwyg) {
            this._galleryWysiwyg.destroy();
            this._galleryWysiwyg = null;
        }
        this._super(...arguments);
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Titre + email obligatoires (injecte le champ email sur les anciens blocs).
     *
     * @private
     */
    _ensureRequiredFields() {
        const titleInput = this.el.querySelector(
            "#s_wiki_gallery_name, .s_wiki_gallery_form input[name='name']"
        );
        if (titleInput) {
            titleInput.required = true;
            titleInput.setAttribute("required", "required");
            if (!titleInput.placeholder) {
                titleInput.placeholder = "Titre de votre article";
            }
        }
        const titleLabel =
            this.el.querySelector("label[for='s_wiki_gallery_name']") ||
            titleInput?.closest(".col-md-6, .col-12, .mb-3, div")?.querySelector("label");
        if (titleLabel && /titre/i.test(titleLabel.textContent || "")) {
            titleLabel.textContent = "Titre *";
        }

        const form = this.el.querySelector(".s_wiki_gallery_form");
        if (!form) {
            return;
        }
        let emailInput = form.querySelector(
            "#s_wiki_gallery_email, input[name='contributor_email']"
        );
        if (!emailInput) {
            const row = form.querySelector(".row.g-3") || form;
            const wrap = document.createElement("div");
            wrap.className = "col-md-6";
            wrap.innerHTML =
                '<label class="form-label" for="s_wiki_gallery_email">Email *</label>' +
                '<input type="email" class="form-control" id="s_wiki_gallery_email" ' +
                'name="contributor_email" maxlength="120" required="required" ' +
                'autocomplete="email" placeholder="vous@example.com"/>';
            const textCol = form.querySelector("#s_wiki_gallery_text")?.closest(".col-12, [class*='col']");
            if (textCol && textCol.parentNode === row) {
                row.insertBefore(wrap, textCol);
            } else {
                const contributorCol = form
                    .querySelector("#s_wiki_gallery_contributor")
                    ?.closest(".col-md-6, [class*='col']");
                if (contributorCol && contributorCol.parentNode) {
                    contributorCol.parentNode.insertBefore(wrap, contributorCol.nextSibling);
                } else {
                    row.appendChild(wrap);
                }
            }
            emailInput = wrap.querySelector("input");
        }
        if (emailInput) {
            emailInput.required = true;
            emailInput.setAttribute("required", "required");
            emailInput.type = "email";
            if (!emailInput.placeholder) {
                emailInput.placeholder = "vous@example.com";
            }
        }
        const emailLabel = this.el.querySelector("label[for='s_wiki_gallery_email']");
        if (emailLabel) {
            emailLabel.textContent = "Email *";
        }

        if (!form.querySelector('input[name="media"]')) {
            const wrap = document.createElement("div");
            wrap.className = "col-12";
            wrap.innerHTML =
                '<label class="form-label" for="s_wiki_gallery_media">Vidéo ou audio (optionnel)</label>' +
                '<input type="file" class="form-control" id="s_wiki_gallery_media" name="media" ' +
                'accept="video/mp4,audio/mpeg,audio/mp4,.mp4,.mp3,.m4a"/>' +
                '<div class="form-text">MP4 — 50 Mo max. MP3 ou M4A — 20 Mo max.</div>';
            const submitCol = form.querySelector(".s_wiki_gallery_submit")?.closest(".col-12");
            const row = form.querySelector(".row.g-3") || form;
            if (submitCol && submitCol.parentNode) {
                submitCol.parentNode.insertBefore(wrap, submitCol);
            } else {
                row.appendChild(wrap);
            }
        }

        const intro = this.el.querySelector(
            ".s_wiki_gallery_form_wrap > p.text-muted, .s_wiki_gallery_form_panel > p.text-muted"
        );
        if (intro && /^Déposez une photo et un texte\./.test((intro.textContent || "").trim())) {
            intro.textContent =
                "Déposez une photo et un texte. Vous pouvez aussi joindre une vidéo ou une piste audio. Un valideur Wiki vérifiera avant publication.";
        }
    },

    /**
     * Bouton en tête de bibliothèque ; le formulaire reste replié
     * tant que le visiteur ne l'ouvre pas.
     * Les pages déjà publiées (formulaire sous les articles) sont
     * réorganisées ici, sans réenregistrement du bloc.
     *
     * @private
     */
    _prepareContributionToggle() {
        const wrap = this.el.querySelector(".s_wiki_gallery_form_wrap");
        if (!wrap) {
            return;
        }
        const editor = this.options.wysiwyg?.odooEditor;
        editor?.observerUnactive?.();
        try {
            let contribute = wrap.closest(".s_wiki_gallery_contribute");
            if (!contribute) {
                contribute = document.createElement("div");
                contribute.className = "s_wiki_gallery_contribute o_not_editable";
                wrap.parentNode.insertBefore(contribute, wrap);
                contribute.appendChild(wrap);
            }
            let btn = contribute.querySelector(".s_wiki_gallery_toggle");
            if (!btn) {
                btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-primary s_wiki_gallery_toggle";
                btn.textContent = "Proposer une contribution";
                contribute.insertBefore(btn, wrap);
            }
            const duplicateId =
                wrap.id && document.querySelectorAll(`#${CSS.escape(wrap.id)}`).length > 1;
            if (!wrap.id || duplicateId) {
                const index = Math.max(
                    0,
                    [...document.querySelectorAll(".s_wiki_gallery")].indexOf(this.el)
                );
                wrap.id = `s_wiki_gallery_form_panel_${this._getGalleryId() || 0}_${index}`;
            }
            btn.setAttribute("aria-controls", wrap.id);
            btn.setAttribute("aria-expanded", "false");
            wrap.hidden = true;
            wrap.classList.remove("mt-5");
            const title = wrap.querySelector(":scope > .s_wiki_gallery_form_title");
            if (title) {
                title.hidden = true;
            }
            const list = this.el.querySelector(".s_wiki_gallery_list");
            if (
                list &&
                list.parentNode &&
                contribute.parentNode === list.parentNode &&
                contribute.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_PRECEDING
            ) {
                list.parentNode.insertBefore(contribute, list);
            }
        } finally {
            editor?.observerActive?.();
        }
    },

    /**
     * @private
     * @param {boolean} open
     */
    _setContributionOpen(open) {
        const btn = this.el.querySelector(".s_wiki_gallery_toggle");
        const wrap = this.el.querySelector(".s_wiki_gallery_form_wrap");
        if (btn) {
            btn.setAttribute("aria-expanded", open ? "true" : "false");
        }
        if (wrap) {
            wrap.hidden = !open;
        }
        if (open && !this.editableMode) {
            this._initTextEditor();
        }
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onToggleContribution(ev) {
        ev.preventDefault();
        const expanded = ev.currentTarget.getAttribute("aria-expanded") === "true";
        this._setContributionOpen(!expanded);
    },

    /**
     * @private
     * @param {File} file
     * @returns {"audio"|"video"|null}
     */
    _classifyMediaFile(file) {
        const name = (file?.name || "").toLowerCase();
        const ext = name.includes(".") ? name.split(".").pop() : "";
        if (ext === "mp3" || ext === "m4a") {
            return "audio";
        }
        if (ext === "mp4") {
            return "video";
        }
        const type = (file?.type || "").toLowerCase();
        if (type === "audio/mpeg" || type === "audio/mp4" || type === "audio/x-m4a") {
            return "audio";
        }
        if (type === "video/mp4") {
            return "video";
        }
        return null;
    },

    _getGalleryId() {
        const raw = this.el.dataset.galleryId;
        if (!raw) {
            return null;
        }
        const parsed = parseInt(raw, 10);
        return Number.isFinite(parsed) ? parsed : null;
    },

    /**
     * Remet le formulaire au HTML d'origine.
     *
     * loadWysiwygFromTextarea déplace le textarea en fin de formulaire.
     * Si la page Wiki est ensuite enregistrée, ce DOM est figé : l'éditeur
     * reste dans le champ Texte et un second est recréé sous le bouton.
     *
     * @private
     * @returns {HTMLTextAreaElement|null}
     */
    _canonicalizeForm() {
        if (this._galleryWysiwyg) {
            const wysiwyg = this._galleryWysiwyg;
            this._galleryWysiwyg = null;
            try {
                wysiwyg.destroy();
            } catch {
                // Le DOM a déjà été retiré.
            }
        }
        const form = this.el.querySelector(".s_wiki_gallery_form");
        if (!form) {
            return null;
        }
        const textareas = [
            ...form.querySelectorAll("textarea[name='text'], textarea#s_wiki_gallery_text"),
        ];
        const textarea = textareas[0] || null;
        textareas.slice(1).forEach((node) => node.remove());

        form.querySelectorAll(
            ".o_wysiwyg_wrapper, .note-editable, .odoo-editor-editable, .o_wysiwyg_resizer, .o_wysiwyg_loading, .o_table_ui_container"
        ).forEach((node) => node.remove());

        [...form.querySelectorAll(".o_wysiwyg_textarea_wrapper")].forEach((wrapper) => {
            const parent = wrapper.parentNode;
            if (!parent) {
                return;
            }
            while (wrapper.firstChild) {
                parent.insertBefore(wrapper.firstChild, wrapper);
            }
            wrapper.remove();
        });

        let field = textarea && textarea.isConnected
            ? textarea
            : form.querySelector("textarea[name='text'], textarea#s_wiki_gallery_text");
        if (!field) {
            field = document.createElement("textarea");
            field.rows = 6;
            field.required = true;
            field.placeholder = "Rédigez votre article : titres, listes, liens, mise en forme…";
        }
        field.id = "s_wiki_gallery_text";
        field.name = "text";
        field.removeAttribute("style");
        field.classList.remove("o_wysiwyg_loader");
        field.classList.add("form-control");

        const label = form.querySelector("label[for='s_wiki_gallery_text']");
        const hint = form.querySelector(".form-text");
        const host = (label && label.parentElement) || (hint && hint.parentElement);
        if (host) {
            if (hint && hint.parentElement === host) {
                host.insertBefore(field, hint);
            } else if (label && label.parentElement === host) {
                label.after(field);
            } else {
                host.appendChild(field);
            }
        }
        return field;
    },

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onCanonicalize(ev) {
        this._canonicalizeForm();
        this._galleryWysiwygLoading = false;
        const wrap = this.el.querySelector(".s_wiki_gallery_form_wrap");
        if (ev.detail && ev.detail.reinit && !this.editableMode && wrap && !wrap.hidden) {
            this._initTextEditor();
        }
    },

    async _initTextEditor() {
        if (this._galleryWysiwyg || this._galleryWysiwygLoading || this.editableMode) {
            return;
        }
        this._galleryWysiwygLoading = true;
        const textarea = this._canonicalizeForm();
        if (!textarea) {
            this._galleryWysiwygLoading = false;
            return;
        }
        // Anciennes instances du bloc : wrapper manquant (DOMContentLoaded déjà passé).
        if (!textarea.closest(".o_wysiwyg_textarea_wrapper")) {
            const wrapper = document.createElement("div");
            wrapper.classList.add("position-relative", "o_wysiwyg_textarea_wrapper");
            textarea.parentNode.insertBefore(wrapper, textarea);
            wrapper.appendChild(textarea);
            textarea.classList.add("o_wysiwyg_loader");
            textarea.removeAttribute("maxlength");
        }
        try {
            this._galleryWysiwyg = await loadWysiwygFromTextarea(this, textarea, {
                value: textarea.value || "",
                resizable: true,
                height: 280,
                userGeneratedContent: true,
                styleInline: true,
                allowCommandImage: false,
                allowCommandVideo: false,
                toolbarOptions: {
                    showColors: false,
                    showFontSize: true,
                    showHistory: true,
                    showHeading1: false,
                    showHeading2: true,
                    showHeading3: true,
                    showLink: true,
                    showImageEdit: false,
                    showImageWidth: false,
                },
                recordInfo: {
                    res_model: "wiki.gallery.item",
                    res_id: 0,
                },
            });
        } catch {
            this._galleryWysiwyg = null;
        } finally {
            this._galleryWysiwygLoading = false;
        }
    },

    /**
     * @private
     * @returns {string}
     */
    _getEditorHtml() {
        if (this._galleryWysiwyg) {
            return this._galleryWysiwyg.getValue() || "";
        }
        return this.el.querySelector('[name="text"]')?.value || "";
    },

    /**
     * @private
     * @param {string} html
     * @returns {boolean}
     */
    _isHtmlEmpty(html) {
        const tmp = document.createElement("div");
        tmp.innerHTML = html || "";
        const plain = (tmp.textContent || "").replace(/\u00a0/g, " ").trim();
        return !plain;
    },

    /**
     * @private
     */
    _resetEditor() {
        const textarea = this.el.querySelector("#s_wiki_gallery_text");
        if (textarea) {
            textarea.value = "";
        }
        if (this._galleryWysiwyg) {
            this._galleryWysiwyg.setValue("<p><br></p>");
        }
    },

    async _loadGallery() {
        const listEl = this.el.querySelector("[data-wiki-gallery-list]");
        if (!listEl) {
            return;
        }
        const galleryId = this._getGalleryId();
        this._itemsById = {};
        if (!galleryId) {
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            listEl.innerHTML =
                '<p class="text-muted mb-0 s_wiki_gallery_empty">' +
                "Sélectionnez une bibliothèque dans les options du bloc." +
                "</p>";
            this.options.wysiwyg?.odooEditor?.observerActive?.();
            return;
        }
        try {
            const res = await jsonrpc("/wiki/gallery/list", {gallery_id: galleryId});
            const items = (res && res.items) || [];
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            if (!items.length) {
                listEl.innerHTML =
                    '<p class="text-muted mb-0 s_wiki_gallery_empty">Aucune contribution publiée pour le moment.</p>';
            } else {
                const grid = document.createElement("div");
                grid.className = "s_wiki_gallery_grid";
                items.forEach((item) => {
                    this._itemsById[item.id] = item;
                    grid.appendChild(this._buildTileEl(item));
                });
                listEl.innerHTML = "";
                listEl.appendChild(grid);
            }
            this.options.wysiwyg?.odooEditor?.observerActive?.();
            this._openLinkedArticle();
        } catch {
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            listEl.innerHTML =
                '<p class="text-muted mb-0 s_wiki_gallery_empty">Bibliothèque indisponible.</p>';
            this.options.wysiwyg?.odooEditor?.observerActive?.();
        }
    },

    /**
     * Tuile : photo + titre + bibliothèque + résumé.
     *
     * @private
     * @param {Object} item
     * @returns {HTMLElement}
     */
    _buildTileEl(item) {
        const tile = document.createElement("a");
        tile.className = "s_wiki_gallery_tile";
        tile.href = `/wiki/article/${item.id}`;
        tile.dataset.itemId = String(item.id);
        tile.setAttribute(
            "aria-label",
            `Ouvrir l'article : ${item.name || "Sans titre"}`
        );

        const media = document.createElement("div");
        media.className = "s_wiki_gallery_tile_media";
        const img = document.createElement("img");
        img.src = item.image_url;
        img.alt = item.name || "Contribution Wiki";
        img.loading = "lazy";
        media.appendChild(img);
        if (item.media_kind === "video" || item.media_kind === "audio") {
            const badge = document.createElement("span");
            badge.className = "s_wiki_gallery_tile_badge";
            badge.textContent = item.media_kind === "video" ? "Vidéo" : "Audio";
            media.appendChild(badge);
        }

        const body = document.createElement("div");
        body.className = "s_wiki_gallery_tile_body";

        const title = document.createElement("h3");
        title.className = "s_wiki_gallery_tile_title";
        title.textContent = item.name || "Sans titre";
        body.appendChild(title);

        if (item.gallery_name) {
            const cat = document.createElement("p");
            cat.className = "s_wiki_gallery_tile_category";
            cat.textContent = item.gallery_name;
            body.appendChild(cat);
        }

        const summary = document.createElement("p");
        summary.className = "s_wiki_gallery_tile_summary";
        summary.textContent = item.summary || "";
        body.appendChild(summary);

        tile.appendChild(media);
        tile.appendChild(body);
        return tile;
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onTileClick(ev) {
        if (this.editableMode) {
            ev.preventDefault();
        }
    },

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onTileKeydown(ev) {
        if (!this.editableMode) {
            return;
        }
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
        }
    },

    /**
     * Ouvre l'article ciblé par ?wiki_item= (résultat de recherche Wiki).
     *
     * @private
     */
    _openLinkedArticle() {
        if (this.editableMode) {
            return;
        }
        let raw = null;
        try {
            raw = new URLSearchParams(window.location.search).get("wiki_item");
        } catch {
            return;
        }
        const id = parseInt(raw, 10);
        if (!Number.isFinite(id) || !this._itemsById[id]) {
            return;
        }
        window.location.replace(`/wiki/article/${id}`);
    },

    /**
     * @private
     * @param {number} itemId
     */
    _openArticle(itemId) {
        const item = this._itemsById[itemId];
        if (!item) {
            return;
        }
        this._closeArticle();

        const modal = document.createElement("div");
        modal.className = "s_wiki_gallery_modal";
        modal.setAttribute("role", "dialog");
        modal.setAttribute("aria-modal", "true");
        modal.setAttribute("aria-label", item.name || "Article");

        const backdrop = document.createElement("div");
        backdrop.className = "s_wiki_gallery_modal_backdrop";
        backdrop.addEventListener("click", () => this._closeArticle());

        const dialog = document.createElement("div");
        dialog.className = "s_wiki_gallery_modal_dialog";

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "s_wiki_gallery_modal_close";
        closeBtn.setAttribute("aria-label", "Fermer");
        closeBtn.innerHTML = "&times;";
        closeBtn.addEventListener("click", () => this._closeArticle());

        const media = document.createElement("div");
        media.className = "s_wiki_gallery_modal_media";
        const img = document.createElement("img");
        img.src = item.image_url;
        img.alt = item.name || "";
        media.appendChild(img);

        const content = document.createElement("div");
        content.className = "s_wiki_gallery_modal_content";

        const title = document.createElement("h2");
        title.className = "s_wiki_gallery_modal_title";
        title.textContent = item.name || "Sans titre";
        content.appendChild(title);

        if (item.gallery_name) {
            const cat = document.createElement("p");
            cat.className = "s_wiki_gallery_modal_category";
            cat.textContent = item.gallery_name;
            content.appendChild(cat);
        }

        const body = document.createElement("div");
        body.className = "s_wiki_gallery_modal_text";
        body.innerHTML = item.text || "";
        content.appendChild(body);

        if (item.contributor_name) {
            const by = document.createElement("p");
            by.className = "s_wiki_gallery_modal_by";
            by.textContent = `— ${item.contributor_name}`;
            content.appendChild(by);
        }

        dialog.appendChild(closeBtn);
        dialog.appendChild(media);
        dialog.appendChild(content);
        modal.appendChild(backdrop);
        modal.appendChild(dialog);
        document.body.appendChild(modal);
        document.body.classList.add("s_wiki_gallery_modal_open");
        document.addEventListener("keydown", this._onModalKeydown);
        this._modalEl = modal;
        closeBtn.focus();
    },

    /**
     * @private
     */
    _closeArticle() {
        if (this._modalEl) {
            this._modalEl.remove();
            this._modalEl = null;
        }
        document.body.classList.remove("s_wiki_gallery_modal_open");
        document.removeEventListener("keydown", this._onModalKeydown);
    },

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onModalKeydown(ev) {
        if (ev.key === "Escape") {
            this._closeArticle();
        }
    },

    /**
     * @private
     * @param {string} message
     * @param {"success"|"danger"|"info"} type
     */
    _showFeedback(message, type) {
        const box = this.el.querySelector(".s_wiki_gallery_feedback");
        if (!box) {
            return;
        }
        box.hidden = false;
        box.className = `s_wiki_gallery_feedback mt-3 alert alert-${type}`;
        box.textContent = message;
    },

    /**
     * @private
     * @param {Event} ev
     */
    async _onSubmit(ev) {
        ev.preventDefault();
        if (this.editableMode) {
            this._showFeedback("Le dépôt est désactivé en mode édition.", "info");
            return;
        }
        const galleryId = this._getGalleryId();
        if (!galleryId) {
            this._showFeedback(
                "Bibliothèque non configurée : choisissez-la dans les options du bloc.",
                "danger"
            );
            return;
        }
        const form = ev.currentTarget;
        const text = this._getEditorHtml();
        const contributor = (form.querySelector('[name="contributor_name"]')?.value || "").trim();
        const email = (form.querySelector('[name="contributor_email"]')?.value || "").trim();
        const name = (form.querySelector('[name="name"]')?.value || "").trim();
        const fileInput = form.querySelector('[name="image"]');
        const file = fileInput?.files?.[0];
        const mediaInput = form.querySelector('[name="media"]');
        const mediaFile = mediaInput?.files?.[0];
        const btn = form.querySelector(".s_wiki_gallery_submit");

        if (!name) {
            this._showFeedback("Le titre est obligatoire.", "danger");
            form.querySelector('[name="name"]')?.focus();
            return;
        }
        if (!email) {
            this._showFeedback("L'email est obligatoire.", "danger");
            form.querySelector('[name="contributor_email"]')?.focus();
            return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            this._showFeedback("Veuillez saisir une adresse email valide.", "danger");
            form.querySelector('[name="contributor_email"]')?.focus();
            return;
        }
        if (this._isHtmlEmpty(text)) {
            this._showFeedback("Le texte est obligatoire.", "danger");
            return;
        }
        if (!file) {
            this._showFeedback("La photo est obligatoire.", "danger");
            return;
        }
        if (file.size > MAX_IMAGE_BYTES) {
            this._showFeedback("L'image est trop volumineuse (max. 5 Mo).", "danger");
            return;
        }
        if (mediaFile) {
            const mediaKind = this._classifyMediaFile(mediaFile);
            if (!mediaKind) {
                this._showFeedback(
                    "Formats acceptés : MP4 (vidéo), MP3 ou M4A (audio).",
                    "danger"
                );
                return;
            }
            if (mediaKind === "audio" && mediaFile.size > MAX_AUDIO_BYTES) {
                this._showFeedback("La piste audio est trop volumineuse (max. 20 Mo).", "danger");
                return;
            }
            if (mediaKind === "video" && mediaFile.size > MAX_VIDEO_BYTES) {
                this._showFeedback("La vidéo est trop volumineuse (max. 50 Mo).", "danger");
                return;
            }
        }

        if (btn) {
            btn.disabled = true;
        }
        try {
            if (this._galleryWysiwyg?.savePendingImages) {
                await this._galleryWysiwyg.savePendingImages();
            }
            const body = new FormData();
            body.append("csrf_token", odoo.csrf_token || "");
            body.append("text", this._getEditorHtml());
            body.append("image", file, file.name);
            body.append("contributor_name", contributor);
            body.append("contributor_email", email);
            body.append("name", name);
            body.append("gallery_id", String(galleryId));
            if (mediaFile) {
                body.append("media", mediaFile, mediaFile.name);
            }
            const response = await fetch("/wiki/gallery/submit", {
                method: "POST",
                body,
                credentials: "same-origin",
            });
            if (response.status === 413) {
                this._showFeedback("Le fichier est trop volumineux.", "danger");
                return;
            }
            let res;
            try {
                res = await response.json();
            } catch {
                res = null;
            }
            if (res && res.ok) {
                if (res.needs_verification) {
                    this._showVerificationStep(res.token, res.email, res.message);
                } else {
                    this._showFeedback(res.message || "Contribution envoyée.", "success");
                    form.reset();
                    this._resetEditor();
                }
            } else {
                this._showFeedback(
                    (res && res.message) || "Envoi impossible.",
                    "danger"
                );
            }
        } catch {
            this._showFeedback("Une erreur est survenue lors de l'envoi.", "danger");
        } finally {
            if (btn) {
                btn.disabled = false;
            }
        }
    },

    /**
     * Affiche l'étape de saisie du code reçu par email.
     *
     * @private
     * @param {string} token
     * @param {string} email
     * @param {string} [message]
     */
    _showVerificationStep(token, email, message) {
        this._pendingToken = token || "";
        this._setContributionOpen(true);
        const form = this.el.querySelector(".s_wiki_gallery_form");
        if (form) {
            form.hidden = true;
        }
        let panel = this.el.querySelector(".s_wiki_gallery_verify");
        if (!panel) {
            panel = document.createElement("div");
            panel.className = "s_wiki_gallery_verify mt-3";
            panel.innerHTML =
                '<p class="s_wiki_gallery_verify_intro text-muted mb-3"></p>' +
                '<div class="row g-3 align-items-end">' +
                '<div class="col-md-6">' +
                '<label class="form-label" for="s_wiki_gallery_verify_code">Code reçu par email *</label>' +
                '<input type="text" class="form-control s_wiki_gallery_verify_code" ' +
                'id="s_wiki_gallery_verify_code" inputmode="numeric" autocomplete="one-time-code" ' +
                'maxlength="8" placeholder="000000"/>' +
                "</div>" +
                '<div class="col-md-6 d-flex flex-wrap gap-2">' +
                '<button type="button" class="btn btn-primary s_wiki_gallery_verify_confirm">Confirmer</button>' +
                '<button type="button" class="btn btn-outline-secondary s_wiki_gallery_verify_cancel">Annuler</button>' +
                "</div></div>";
            const wrap = this.el.querySelector(".s_wiki_gallery_form_wrap") || this.el;
            wrap.appendChild(panel);
        }
        panel.hidden = false;
        const intro = panel.querySelector(".s_wiki_gallery_verify_intro");
        if (intro) {
            intro.textContent =
                message ||
                `Un code a été envoyé à ${email || "votre adresse email"}. Saisissez-le pour finaliser.`;
        }
        const codeInput = panel.querySelector(".s_wiki_gallery_verify_code");
        if (codeInput) {
            codeInput.value = "";
            codeInput.focus();
        }
        this._showFeedback(
            message || "Vérifiez votre boîte mail et saisissez le code.",
            "info"
        );
    },

    /**
     * @private
     */
    _hideVerificationStep() {
        this._pendingToken = null;
        const panel = this.el.querySelector(".s_wiki_gallery_verify");
        if (panel) {
            panel.hidden = true;
        }
        const form = this.el.querySelector(".s_wiki_gallery_form");
        if (form) {
            form.hidden = false;
        }
    },

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onVerifyCodeKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._onVerifyConfirm(ev);
        }
    },

    /**
     * @private
     * @param {Event} ev
     */
    async _onVerifyConfirm(ev) {
        ev.preventDefault();
        if (this.editableMode || !this._pendingToken) {
            return;
        }
        const panel = this.el.querySelector(".s_wiki_gallery_verify");
        const code = (panel?.querySelector(".s_wiki_gallery_verify_code")?.value || "").trim();
        const confirmBtn = panel?.querySelector(".s_wiki_gallery_verify_confirm");
        if (!code) {
            this._showFeedback("Saisissez le code reçu par email.", "danger");
            return;
        }
        if (confirmBtn) {
            confirmBtn.disabled = true;
        }
        try {
            const res = await jsonrpc("/wiki/gallery/verify", {
                token: this._pendingToken,
                code,
            });
            if (res && res.ok) {
                this._hideVerificationStep();
                const form = this.el.querySelector(".s_wiki_gallery_form");
                if (form) {
                    form.reset();
                }
                this._resetEditor();
                this._showFeedback(res.message || "Contribution envoyée.", "success");
            } else {
                this._showFeedback(
                    (res && res.message) || "Code incorrect.",
                    "danger"
                );
                if (res && res.deleted) {
                    this._hideVerificationStep();
                    const form = this.el.querySelector(".s_wiki_gallery_form");
                    if (form) {
                        form.reset();
                    }
                    this._resetEditor();
                }
            }
        } catch {
            this._showFeedback("Une erreur est survenue lors de la confirmation.", "danger");
        } finally {
            if (confirmBtn) {
                confirmBtn.disabled = false;
            }
        }
    },

    /**
     * @private
     * @param {Event} ev
     */
    async _onVerifyCancel(ev) {
        ev.preventDefault();
        if (!this._pendingToken) {
            this._hideVerificationStep();
            return;
        }
        const token = this._pendingToken;
        try {
            await jsonrpc("/wiki/gallery/verify/cancel", {token});
        } catch {
            // ignore
        }
        this._hideVerificationStep();
        const form = this.el.querySelector(".s_wiki_gallery_form");
        if (form) {
            form.reset();
        }
        this._resetEditor();
        this._showFeedback("Contribution annulée.", "info");
    },
});

publicWidget.registry.WikiGallerySnippet = WikiGallerySnippet;

export default WikiGallerySnippet;
