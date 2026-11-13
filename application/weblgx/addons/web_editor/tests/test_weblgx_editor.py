# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

import weblgx.tests

@weblgx.tests.tagged("post_install", "-at_install")
class TestWeblgxEditor(weblgx.tests.HttpCase):

    def test_weblgx_editor_suite(self):
        self.browser_js('/web_editor/tests', "", "", login='admin', timeout=1800)
