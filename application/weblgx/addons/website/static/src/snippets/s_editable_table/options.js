/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";

const DEFAULT_HEADER_BG = "#191970";
const DEFAULT_BODY_BG = "#F8F9FA";
const DEFAULT_BORDER_COLOR = "#dee2e6";

const CELL_SELECTOR = ".s_editable_table_table th, .s_editable_table_table td";
const SELECTED_CLASS = "o_editable_table_cell_selected";

options.registry.EditableTable = options.Class.extend({
    events: Object.assign({}, options.Class.prototype.events, {
        [`mousedown ${CELL_SELECTOR}`]: "_onCellMouseDown",
        [`focusin ${CELL_SELECTOR}`]: "_onCellFocus",
    }),

    start() {
        this.tableEl = this.$target.find("table.s_editable_table_table")[0];
        this.selectedCell = null;
        this._ensureWrapperDefaults();
        this._ensureStyleDefaults();
        this._applyStyles();
        return this._super(...arguments);
    },

    async updateUI() {
        await this._super(...arguments);
        this._applyStyles();
    },

    cleanForSave() {
        this.tableEl.querySelectorAll(`.${SELECTED_CLASS}`).forEach((el) => {
            el.classList.remove(SELECTED_CLASS);
        });
        this.tableEl.querySelectorAll("th, td").forEach((cell) => {
            cell.colSpan = 1;
            cell.rowSpan = 1;
        });
        delete this.$target[0].dataset.etableSelectedRow;
        delete this.$target[0].dataset.etableSelectedCol;
    },

    addRow() {
        const cell = this._getTargetCell();
        const colCount = this._getLogicalColumnCount();
        if (!colCount) {
            return;
        }
        const insertRowIndex = cell ? cell.parentElement.rowIndex + 1 : this.tableEl.rows.length;
        this._insertRowAt(insertRowIndex, colCount);
        this.$target.trigger("content_changed");
        this.updateUI();
    },

    removeRow() {
        const cell = this._getTargetCell();
        const tbody = this.tableEl.tBodies[0];
        if (!tbody || tbody.rows.length <= 1) {
            return;
        }
        const row = cell ? cell.parentElement : tbody.rows[tbody.rows.length - 1];
        if (!row || row.parentElement.tagName === "THEAD") {
            return;
        }
        row.remove();
        this._selectCell(null);
        this.$target.trigger("content_changed");
        this.updateUI();
    },

    addColumn() {
        const cell = this._getTargetCell();
        const insertAfterIndex = cell ? cell.cellIndex : this._getLogicalColumnCount() - 1;
        for (const row of this.tableEl.rows) {
            const isHeader = row.parentElement && row.parentElement.tagName === "THEAD";
            const tag = isHeader ? "th" : "td";
            const refCell = insertAfterIndex >= 0 ? row.cells[insertAfterIndex] : null;
            const newCell = this._makeCell(tag, this._getDefaultColumnLabel(row.cells.length + 1, isHeader));
            if (refCell) {
                refCell.insertAdjacentElement("afterend", newCell);
            } else {
                row.appendChild(newCell);
            }
        }
        this.$target.trigger("content_changed");
        this.updateUI();
    },

    removeColumn() {
        const cell = this._getTargetCell();
        if (this._getLogicalColumnCount() <= 1) {
            return;
        }
        const cellIndex = cell ? cell.cellIndex : this._getLogicalColumnCount() - 1;
        for (const row of this.tableEl.rows) {
            if (row.cells.length > 1 && row.cells[cellIndex]) {
                row.cells[cellIndex].remove();
            }
        }
        this._selectCell(null);
        this.$target.trigger("content_changed");
        this.updateUI();
    },

    setHeaderBg(previewMode, widgetValue) {
        if (widgetValue) {
            this.$target[0].dataset.headerBg = widgetValue;
            this.$target[0].style.setProperty("--etable-header-bg", widgetValue);
        }
    },

    setBodyBg(previewMode, widgetValue) {
        if (widgetValue) {
            this.$target[0].dataset.bodyBg = widgetValue;
            this.$target[0].style.setProperty("--etable-body-bg", widgetValue);
        }
    },

    setBorderColor(previewMode, widgetValue) {
        if (widgetValue) {
            this.$target[0].dataset.borderColor = widgetValue;
            this.$target[0].style.setProperty("--etable-border-color", widgetValue);
        }
    },

    _onCellMouseDown(ev) {
        ev.stopPropagation();
        this._selectCell(ev.currentTarget);
    },

    _onCellFocus(ev) {
        this._selectCell(ev.currentTarget);
    },

    _computeWidgetState(methodName) {
        switch (methodName) {
            case "setHeaderBg":
                return this.$target[0].dataset.headerBg || DEFAULT_HEADER_BG;
            case "setBodyBg":
                return this.$target[0].dataset.bodyBg || DEFAULT_BODY_BG;
            case "setBorderColor":
                return this.$target[0].dataset.borderColor || DEFAULT_BORDER_COLOR;
        }
        return this._super(...arguments);
    },

    _computeWidgetVisibility(widgetName) {
        switch (widgetName) {
            case "remove_row_opt":
                return this.tableEl.querySelectorAll("tbody tr").length > 1;
            case "remove_col_opt":
                return this._getLogicalColumnCount() > 1;
        }
        return this._super(...arguments);
    },

    _getTargetCell() {
        const active = document.activeElement;
        if (active && this.tableEl.contains(active) && /^(TD|TH)$/i.test(active.tagName)) {
            return active;
        }
        if (this.selectedCell && this.tableEl.contains(this.selectedCell)) {
            return this.selectedCell;
        }
        const selected = this.tableEl.querySelector(`.${SELECTED_CLASS}`);
        if (selected) {
            return selected;
        }
        const target = this.$target[0];
        const rowIndex = parseInt(target.dataset.etableSelectedRow, 10);
        const colIndex = parseInt(target.dataset.etableSelectedCol, 10);
        if (!Number.isNaN(rowIndex) && !Number.isNaN(colIndex)) {
            const row = this.tableEl.rows[rowIndex];
            if (row && row.cells[colIndex]) {
                return row.cells[colIndex];
            }
        }
        return null;
    },

    _selectCell(cell) {
        if (this.selectedCell) {
            this.selectedCell.classList.remove(SELECTED_CLASS);
        }
        this.selectedCell = cell;
        const target = this.$target[0];
        if (cell) {
            cell.classList.add(SELECTED_CLASS);
            target.dataset.etableSelectedRow = String(cell.parentElement.rowIndex);
            target.dataset.etableSelectedCol = String(cell.cellIndex);
        } else {
            delete target.dataset.etableSelectedRow;
            delete target.dataset.etableSelectedCol;
        }
    },

    _getLogicalColumnCount() {
        const firstRow = this.tableEl.rows[0];
        return firstRow ? firstRow.cells.length : 0;
    },

    _insertRowAt(insertRowIndex, colCount) {
        const theadRowCount = this.tableEl.tHead ? this.tableEl.tHead.rows.length : 0;
        if (insertRowIndex <= theadRowCount) {
            insertRowIndex = theadRowCount + 1;
        }
        const tr = document.createElement("tr");
        for (let c = 0; c < colCount; c++) {
            tr.appendChild(this._makeCell("td", _t("Contenu")));
        }
        const tbody = this.tableEl.tBodies[0] || this.tableEl.createTBody();
        const bodyInsertIndex = insertRowIndex - theadRowCount;
        if (bodyInsertIndex >= tbody.rows.length) {
            tbody.appendChild(tr);
        } else {
            tbody.insertBefore(tr, tbody.rows[bodyInsertIndex]);
        }
    },

    _getDefaultColumnLabel(index, isHeader) {
        return isHeader ? `${_t("Colonne")} ${index}` : _t("Contenu");
    },

    _makeCell(tag, text) {
        const cell = document.createElement(tag);
        cell.setAttribute("contenteditable", "true");
        cell.textContent = text;
        return cell;
    },

    _applyStyles() {
        const target = this.$target[0];
        const headerBg = target.dataset.headerBg || DEFAULT_HEADER_BG;
        const bodyBg = target.dataset.bodyBg || DEFAULT_BODY_BG;
        const borderColor = target.dataset.borderColor || DEFAULT_BORDER_COLOR;
        target.style.setProperty("--etable-header-bg", headerBg);
        target.style.setProperty("--etable-body-bg", bodyBg);
        target.style.setProperty("--etable-border-color", borderColor);
    },

    _ensureStyleDefaults() {
        const target = this.$target[0];
        if (!target.dataset.headerBg) {
            target.dataset.headerBg = DEFAULT_HEADER_BG;
        }
        if (!target.dataset.bodyBg) {
            target.dataset.bodyBg = DEFAULT_BODY_BG;
        }
        if (!target.dataset.borderColor) {
            target.dataset.borderColor = DEFAULT_BORDER_COLOR;
        }
    },

    _ensureWrapperDefaults() {
        const wrapper = this.$target.find(".s_editable_table_wrapper")[0];
        if (!wrapper) {
            return;
        }
        const widthClasses = ["w-25", "w-50", "w-75", "w-100"];
        if (!widthClasses.some((cls) => wrapper.classList.contains(cls))) {
            wrapper.classList.add("w-75", "mx-auto");
        }
    },
});
