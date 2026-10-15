/** @weblgx-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

const DEFAULT_IMAGE = "/wiki_knowledge/static/src/img/wiki_logo.png";

/**
 * Building block : derniers articles Wiki (image + titre + date).
 */
const WikiLatestArticlesSnippet = publicWidget.Widget.extend({
    selector: ".s_wiki_latest_articles",
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
        const raw = parseInt(this.el.dataset.limit || "5", 10);
        if (!Number.isFinite(raw)) {
            return 5;
        }
        return Math.min(Math.max(raw, 1), 20);
    },

    _getDefaultImage() {
        const src = (this.el.dataset.defaultImage || "").trim();
        return src || DEFAULT_IMAGE;
    },

    async _loadArticles() {
        const listEl = this.el.querySelector("[data-wiki-latest-list]");
        if (!listEl) {
            return;
        }
        try {
            const res = await jsonrpc("/wiki/api/latest_articles", {
                limit: this._getLimit(),
                default_image: this._getDefaultImage(),
            });
            const items = (res && res.items) || [];
            this.options.wysiwyg?.odooEditor?.observerUnactive?.();
            if (!items.length) {
                listEl.innerHTML =
                    '<p class="text-muted mb-0 s_wiki_latest_articles_empty">' +
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
            listEl.innerHTML =
                '<p class="text-muted mb-0 s_wiki_latest_articles_empty">' +
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
        const link = document.createElement("a");
        link.className = "s_wiki_latest_articles_item";
        link.href = item.url || "/wiki";
        link.title = item.name || "";

        const thumb = document.createElement("div");
        thumb.className = "s_wiki_latest_articles_thumb";
        const img = document.createElement("img");
        img.src = item.image_url || this._getDefaultImage();
        img.alt = item.name || "";
        img.loading = "lazy";
        img.onerror = () => {
            if (img.dataset.fallbackApplied) {
                return;
            }
            img.dataset.fallbackApplied = "1";
            img.src = this._getDefaultImage();
        };
        thumb.appendChild(img);

        const body = document.createElement("div");
        body.className = "s_wiki_latest_articles_body";
        const title = document.createElement("h3");
        title.className = "s_wiki_latest_articles_item_title";
        title.textContent = item.name || "";
        body.appendChild(title);
        if (item.meta) {
            const meta = document.createElement("p");
            meta.className = "s_wiki_latest_articles_item_meta";
            meta.textContent = item.meta;
            body.appendChild(meta);
        }
        if (item.date_label) {
            const date = document.createElement("p");
            date.className = "s_wiki_latest_articles_item_date";
            date.textContent = item.date_label;
            body.appendChild(date);
        }

        link.appendChild(thumb);
        link.appendChild(body);
        return link;
    },
});

publicWidget.registry.WikiLatestArticlesSnippet = WikiLatestArticlesSnippet;

export default WikiLatestArticlesSnippet;
