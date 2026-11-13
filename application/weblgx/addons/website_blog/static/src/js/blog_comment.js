/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.blogCommentPublic = publicWidget.Widget.extend({
    selector: ".o_wblog_comment_public",
    events: {
        "submit .o_wblog_comment_form": "_onSubmit",
        "click .o_wblog_comment_verify_btn": "_onVerify",
        "click .o_wblog_comment_cancel": "_onCancel",
        "keydown .o_wblog_comment_code": "_onCodeKey",
    },

    start() {
        this.token = null;
        this.postId = parseInt(this.el.dataset.postId, 10);
        return this._super.apply(this, arguments);
    },

    _setFeedback(message, isError) {
        const node = this.el.querySelector(".o_wblog_comment_feedback");
        if (!node) {
            return;
        }
        node.hidden = !message;
        node.classList.toggle("text-danger", !!isError);
        node.classList.toggle("text-muted", !isError);
        node.textContent = message || "";
    },

    _setBusy(busy) {
        this.el.querySelectorAll("button").forEach((button) => {
            button.disabled = busy;
        });
    },

    async _onSubmit(ev) {
        ev.preventDefault();
        const form = ev.currentTarget;
        const email = (form.querySelector('[name="email"]')?.value || "").trim();
        const message = (form.querySelector('[name="message"]')?.value || "").trim();
        if (!email || !message) {
            this._setFeedback("L'adresse email et le message sont obligatoires.", true);
            return;
        }
        this._setBusy(true);
        try {
            const result = await jsonrpc("/blog/comment/submit", {
                post_id: this.postId,
                email,
                message,
            });
            if (!result || !result.ok) {
                this._setFeedback((result && result.message) || "L'envoi a échoué.", true);
                return;
            }
            this.token = result.token;
            form.hidden = true;
            const verify = this.el.querySelector(".o_wblog_comment_verify");
            if (verify) {
                verify.hidden = false;
            }
            const code = this.el.querySelector(".o_wblog_comment_code");
            if (code) {
                code.value = "";
                code.focus();
            }
            this._setFeedback(result.message || "Un code a été envoyé par email.");
        } catch (_error) {
            this._setFeedback("L'envoi a échoué. Réessayez plus tard.", true);
        } finally {
            this._setBusy(false);
        }
    },

    async _onVerify() {
        const code = (this.el.querySelector(".o_wblog_comment_code")?.value || "").trim();
        if (!this.token || !/^\d{6}$/.test(code)) {
            this._setFeedback("Saisissez le code à 6 chiffres reçu par email.", true);
            return;
        }
        this._setBusy(true);
        try {
            const result = await jsonrpc("/blog/comment/verify", {
                token: this.token,
                code,
            });
            if (!result || !result.ok) {
                this._setFeedback((result && result.message) || "Code incorrect.", true);
                if (result && result.deleted) {
                    this.token = null;
                    const form = this.el.querySelector(".o_wblog_comment_form");
                    const verify = this.el.querySelector(".o_wblog_comment_verify");
                    if (form) {
                        form.hidden = false;
                    }
                    if (verify) {
                        verify.hidden = true;
                    }
                }
                return;
            }
            this.token = null;
            const verify = this.el.querySelector(".o_wblog_comment_verify");
            if (verify) {
                verify.hidden = true;
            }
            this._setFeedback(result.message || "Merci. Votre commentaire sera visible après validation.");
        } catch (_error) {
            this._setFeedback("Impossible de confirmer le code.", true);
        } finally {
            this._setBusy(false);
        }
    },

    async _onCancel() {
        const token = this.token;
        this.token = null;
        const form = this.el.querySelector(".o_wblog_comment_form");
        const verify = this.el.querySelector(".o_wblog_comment_verify");
        if (form) {
            form.hidden = false;
        }
        if (verify) {
            verify.hidden = true;
        }
        this._setFeedback("");
        if (token) {
            try {
                await jsonrpc("/blog/comment/cancel", { token });
            } catch (_error) {
                // Le code expirera de lui-même.
            }
        }
    },

    _onCodeKey(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._onVerify();
        }
    },
});
