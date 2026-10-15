/** @odoo-module **/

import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

const LINK_REGEX = new RegExp("^https?://");
const DOCS_BASE_URL = "https://wiki.loegaux.fr/wiki?page_id=19";

export class DocumentationLink extends Component {
    static template = "web.DocumentationLink";
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: 1 }, // The record is not needed in this widget
        path: { type: String },
    };

    get url() {
        const path = this.props.path;
        if (LINK_REGEX.test(path)) {
            return /odoo\.com\/documentation/i.test(path) ? DOCS_BASE_URL : path;
        }
        return DOCS_BASE_URL;
    }
}

export const documentationLink = {
    component: DocumentationLink,
    extractProps: ({ attrs }) => {
        const { path } = attrs;
        return {
            path,
        };
    },
    additionalClasses: ["d-inline"],
};

registry.category("view_widgets").add("documentation_link", documentationLink);
