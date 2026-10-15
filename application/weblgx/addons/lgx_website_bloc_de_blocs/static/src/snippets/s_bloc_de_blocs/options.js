/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

const COL_CLASSES = {
    1: "col-12",
    2: "col-12 col-lg-6",
    3: "col-12 col-lg-4",
    4: "col-12 col-lg-3",
    5: "col-12 col-lg",
    6: "col-12 col-lg-2",
};

const PLACEHOLDER_HTML = `
<section class="s_text_block">
    <div class="container">
        <p>Déposez ici des blocs (texte, image, vidéo, HTML…).</p>
    </div>
</section>`.trim();

/**
 * Options for "Bloc de blocs": 1–6 columns, each with an oe_structure dropzone.
 */
options.registry.BlocDeBlocs = options.Class.extend({
    /**
     * @see this.selectClass for parameters
     */
    async selectCount(previewMode, widgetValue) {
        const count = Math.min(6, Math.max(1, parseInt(widgetValue, 10) || 1));
        const rowEl = this.$target[0].querySelector(".s_bloc_de_blocs_row");
        if (!rowEl) {
            return;
        }

        let cols = [...rowEl.querySelectorAll(":scope > .s_bloc_de_blocs_col")];

        while (cols.length < count) {
            if (!cols.length) {
                rowEl.appendChild(this._createEmptyColumn());
            } else {
                const clone = cols[cols.length - 1].cloneNode(true);
                this._resetColumn(clone);
                rowEl.appendChild(clone);
            }
            cols = [...rowEl.querySelectorAll(":scope > .s_bloc_de_blocs_col")];
        }
        while (cols.length > count) {
            cols[cols.length - 1].remove();
            cols = [...rowEl.querySelectorAll(":scope > .s_bloc_de_blocs_col")];
        }

        this._applyColClasses(cols, count);
        await new Promise((resolve) => setTimeout(resolve));
        this.trigger_up("activate_snippet", {
            $snippet: this.$(cols[0] || this.$target),
        });
    },

    /**
     * @private
     * @returns {HTMLElement}
     */
    _createEmptyColumn() {
        const col = document.createElement("div");
        col.className = "col-12 col-lg-6 s_bloc_de_blocs_col pt8 pb8";
        col.dataset.name = "Colonne";
        this._resetColumn(col);
        return col;
    },

    /**
     * Reset a column to an empty dropzone (placeholder text block).
     *
     * @private
     * @param {HTMLElement} colEl
     */
    _resetColumn(colEl) {
        colEl.dataset.name = "Colonne";
        let zone = colEl.querySelector(":scope > .s_bloc_de_blocs_dropzone");
        if (!zone) {
            zone = document.createElement("div");
            zone.className = "oe_structure oe_empty s_bloc_de_blocs_dropzone";
            colEl.replaceChildren(zone);
        }
        zone.classList.add("oe_structure", "oe_empty", "s_bloc_de_blocs_dropzone");
        zone.innerHTML = PLACEHOLDER_HTML;
    },

    /**
     * @private
     * @param {HTMLElement[]} cols
     * @param {number} count
     */
    _applyColClasses(cols, count) {
        const className = COL_CLASSES[count] || COL_CLASSES[2];
        for (const col of cols) {
            // Keep utility classes, replace only bootstrap col-* sizing.
            const kept = [...col.classList].filter(
                (c) =>
                    !c.startsWith("col") &&
                    c !== "s_bloc_de_blocs_col"
            );
            col.className = `${className} s_bloc_de_blocs_col ${kept.join(" ")}`.trim();
        }
    },

    /**
     * @override
     */
    _computeWidgetState(methodName) {
        if (methodName === "selectCount") {
            const rowEl = this.$target[0].querySelector(".s_bloc_de_blocs_row");
            if (!rowEl) {
                return "2";
            }
            return String(
                rowEl.querySelectorAll(":scope > .s_bloc_de_blocs_col").length
            );
        }
        return this._super(...arguments);
    },
});

export default {
    BlocDeBlocs: options.registry.BlocDeBlocs,
};
