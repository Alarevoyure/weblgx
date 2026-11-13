/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";

publicWidget.registry.wikiArticleEdit = publicWidget.Widget.extend({
    selector: ".o_wiki_article_edit",
    events: {
        "submit .o_wiki_article_edit_form": "_onSubmit",
        "click .o_wiki_edit_verify_btn": "_onVerify",
        "click .o_wiki_edit_verify_cancel": "_onVerifyCancel",
    },

    async start() {
        await this._super(...arguments);
        this.wysiwyg = null;
        this.verifyToken = null;
        this.submitUrl = this.el.dataset.submitUrl || "";
        this.articleUrl = this.el.dataset.articleUrl || "";
        await this._initWysiwyg();
        return Promise.resolve();
    },

    destroy() {
        if (this.wysiwyg) {
            this.wysiwyg.destroy();
            this.wysiwyg = null;
        }
        return this._super(...arguments);
    },

    async _initWysiwyg() {
        const textarea = this.el.querySelector("#o_wiki_edit_text");
        if (!textarea) {
            return;
        }
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
            });
        } catch (error) {
            console.warn("Wiki article edit: wysiwyg unavailable", error);
        }
    },

    _getTextValue() {
        if (this.wysiwyg) {
            return this.wysiwyg.getValue() || "";
        }
        const textarea = this.el.querySelector("#o_wiki_edit_text");
        return textarea ? textarea.value || "" : "";
    },

    _csrfToken() {
        return (
            document.querySelector('meta[name="csrf_token"]')?.getAttribute("content") ||
            window.odoo?.csrf_token ||
            ""
        );
    },

    _setFeedback(message, isError = false) {
        const box = this.el.querySelector(".o_wiki_edit_feedback");
        if (!box) {
            return;
        }
        box.hidden = !message;
        box.textContent = message || "";
        box.classList.toggle("text-danger", !!isError);
        box.classList.toggle("text-success", !isError && !!message);
    },

    _setBusy(busy) {
        const btn = this.el.querySelector(".o_wiki_edit_submit");
        if (btn) {
            btn.disabled = !!busy;
        }
    },

    _showVerify(show) {
        const panel = this.el.querySelector(".o_wiki_edit_verify");
        if (panel) {
            panel.hidden = !show;
        }
        if (!show) {
            this.verifyToken = null;
            const code = this.el.querySelector("#o_wiki_edit_code");
            if (code) {
                code.value = "";
            }
        }
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        const form = ev.currentTarget;
        const name = (form.querySelector('[name="name"]')?.value || "").trim();
        const email = (form.querySelector('[name="contributor_email"]')?.value || "").trim();
        const contributor = (form.querySelector('[name="contributor_name"]')?.value || "").trim();
        const text = this._getTextValue();
        if (!name) {
            this._setFeedback("Le titre est obligatoire.", true);
            return;
        }
        if (!email) {
            this._setFeedback("L'email est obligatoire.", true);
            return;
        }
        if (!text || !text.replace(/<[^>]+>/g, "").trim()) {
            this._setFeedback("Le texte est obligatoire.", true);
            return;
        }

        const body = new FormData();
        body.append("name", name);
        body.append("contributor_email", email);
        body.append("contributor_name", contributor);
        body.append("text", text);
        body.append("csrf_token", this._csrfToken());
        const image = form.querySelector('[name="image"]')?.files?.[0];
        if (image) {
            body.append("image", image);
        }
        const media = form.querySelector('[name="media"]')?.files?.[0];
        if (media) {
            body.append("media", media);
        }
        if (form.querySelector('[name="clear_media"]')?.checked) {
            body.append("clear_media", "1");
        }

        this._setBusy(true);
        this._setFeedback("Envoi en cours…");
        try {
            const response = await fetch(this.submitUrl, {
                method: "POST",
                body,
                credentials: "same-origin",
            });
            const data = await response.json();
            if (data.error) {
                this._setFeedback(data.message || "Erreur lors de l'envoi.", true);
                return;
            }
            if (data.needs_verification) {
                this.verifyToken = data.token;
                this._showVerify(true);
                this._setFeedback(data.message || "Code envoyé par email.");
                return;
            }
            this._setFeedback(data.message || "Modifications envoyées.");
            window.location.href = data.redirect || this.articleUrl || "/wiki";
        } catch (error) {
            console.error(error);
            this._setFeedback("Impossible d'envoyer les modifications.", true);
        } finally {
            this._setBusy(false);
        }
    },

    async _onVerify() {
        const code = (this.el.querySelector("#o_wiki_edit_code")?.value || "").trim();
        if (!this.verifyToken || !code) {
            this._setFeedback("Saisissez le code reçu par email.", true);
            return;
        }
        this._setBusy(true);
        try {
            const data = await jsonrpc("/wiki/gallery/verify", {
                token: this.verifyToken,
                code,
            });
            if (!data.ok) {
                this._setFeedback(data.message || "Code incorrect.", true);
                if (data.deleted) {
                    this._showVerify(false);
                }
                return;
            }
            this._setFeedback(data.message || "Modifications confirmées.");
            window.location.href = this.articleUrl || "/wiki";
        } catch (error) {
            console.error(error);
            this._setFeedback("Impossible de confirmer le code.", true);
        } finally {
            this._setBusy(false);
        }
    },

    async _onVerifyCancel() {
        if (this.verifyToken) {
            try {
                await jsonrpc("/wiki/gallery/verify/cancel", { token: this.verifyToken });
            } catch (error) {
                console.warn(error);
            }
        }
        this._showVerify(false);
        this._setFeedback("Modification annulée.");
    },
});

export default publicWidget.registry.wikiArticleEdit;
