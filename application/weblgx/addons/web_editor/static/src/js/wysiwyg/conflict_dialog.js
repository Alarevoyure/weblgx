/* @weblgx-module */

import { Component } from "@weblgx/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ConflictDialog extends Component {
    static components = { Dialog };
    static props = ["close","content"];
    static template = 'web_editor.ConflictDialog';
}
