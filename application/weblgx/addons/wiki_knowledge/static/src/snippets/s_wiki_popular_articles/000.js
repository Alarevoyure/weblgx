/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * Building block : articles de bibliothèque les plus ouverts.
 * Photo, titre et bouton, sur une rangée horizontale.
 */
const WikiPopularArticlesSnippet = publicWidget.Widget.extend({
    selector: ".s_wiki_popular_articles",
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        const proms = [this._super(...arguments)];
        proms.push(this._loadArticles());
        return Promise.all(proms);
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    _getLimit() {
        const raw = parseInt(this.el.dataset.limit || "4", 10);
        if (!Number.isFinite(raw)) {
            return 4;
        }
        return Math.min(Math.max(raw, 2), 6);
    },

    async _loadArticles() {
        const listEl = this.el.querySelector("[data-wiki-popular-list]");
        if (!listEl) {
            return;
        }
        try {
            const res = await jsonrpc("/wiki/api/popular_articles", {
                limit: this._getLimit(),
            });
            const items = (res && res.items) || [];
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            listEl.dataset.count = String(items.length);
            if (!items.length) {
                listEl.innerHTML =
                    '<p class="text-muted mb-0 s_wiki_popular_empty">' +
                    "Aucun article publié pour le moment." +
                    "</p>";
            } else {
                listEl.innerHTML = "";
                items.forEach((item) => {
                    listEl.appendChild(this._buildItemEl(item));
                });
            }
            this.options.wysiwyg?.odooEditor?.observerActive?.();
        } catch {
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            listEl.dataset.count = "0";
            listEl.innerHTML =
                '<p class="text-muted mb-0 s_wiki_popular_empty">' +
                "Articles indisponibles." +
                "</p>";
            this.options.wysiwyg?.odooEditor?.observerActive?.();
        }
    },

    /**
     * @private
     * @param {Object} item
     * @returns {HTMLElement}
     */
    _buildItemEl(item) {
        const name = item.name || "Sans titre";
        const link = document.createElement("a");
        link.className = "s_wiki_popular_card";
        link.href = item.url || "/wiki";

        const thumb = document.createElement("div");
        thumb.className = "s_wiki_popular_thumb";
        const img = document.createElement("img");
        img.src = item.image_url || "";
        img.alt = "";
        img.loading = "lazy";
        thumb.appendChild(img);

        const body = document.createElement("div");
        body.className = "s_wiki_popular_body";
        const title = document.createElement("h3");
        title.className = "s_wiki_popular_title";
        title.textContent = name;
        const button = document.createElement("span");
        button.className = "btn btn-primary s_wiki_popular_btn";
        button.textContent = "Découvrir l'article \u2794";
        body.appendChild(title);
        body.appendChild(button);

        link.appendChild(thumb);
        link.appendChild(body);
        return link;
    },
});

publicWidget.registry.WikiPopularArticlesSnippet = WikiPopularArticlesSnippet;

export default WikiPopularArticlesSnippet;
