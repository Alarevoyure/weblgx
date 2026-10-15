/** @odoo-module **/
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("Widgets", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        bar: { string: "Bar", type: "boolean" },
                    },
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("DocumentationLink");

    QUnit.test("documentation_link: relative path", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <widget name="documentation_link"  path="/applications/technical/web/settings/this_is_a_test.html"/>
                </form>`,
        });

        assert.hasAttrValue(
            target.querySelector(".o_doc_link"),
            "href",
            "https://wiki.loegaux.fr/wiki?page_id=19"
        );
    });
    QUnit.test("documentation_link: absoluth path (http)", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <widget name="documentation_link"  path="http://www.odoo.com/"/>
                </form>`,
        });

        assert.hasAttrValue(target.querySelector(".o_doc_link"), "href", "http://www.odoo.com/");
    });
    QUnit.test("documentation_link: absoluth path (https)", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <widget name="documentation_link"  path="https://www.loegaux.fr/"/>
                </form>`,
        });

        assert.hasAttrValue(target.querySelector(".o_doc_link"), "href", "https://www.loegaux.fr/");
    });
    QUnit.test("documentation_link: odoo.com/documentation redirects to Web@LGX docs", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <widget name="documentation_link" path="https://www.loegaux.fr/documentation/17.0/foo.html"/>
                </form>`,
        });

        assert.hasAttrValue(
            target.querySelector(".o_doc_link"),
            "href",
            "https://wiki.loegaux.fr/wiki?page_id=19"
        );
    });
});
