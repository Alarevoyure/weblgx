# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

from weblgx import models, fields


class Users(models.Model):
    _inherit = 'res.users'

    weblgxbot_state = fields.Selection(selection_add=[
        ('onboarding_canned', 'Onboarding canned'),
    ], ondelete={'onboarding_canned': lambda users: users.write({'weblgxbot_state': 'disabled'})})
