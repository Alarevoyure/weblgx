# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

from weblgx import models, fields


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('meeting', 'Meeting')])
