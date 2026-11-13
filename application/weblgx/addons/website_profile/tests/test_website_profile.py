# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

import weblgx.tests
from weblgx.addons.gamification.tests.common import HttpCaseGamification


@weblgx.tests.tagged('post_install', '-at_install')
class TestWebsiteProfile(HttpCaseGamification):
    def test_save_change_description(self):
        weblgx.tests.new_test_user(
            self.env, 'test_user',
            karma=100, website_published=True
        )
        self.start_tour("/", 'website_profile_description', login="admin")
