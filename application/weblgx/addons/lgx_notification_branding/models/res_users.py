# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    notification_type = fields.Selection(
        selection=[
            ("email", "Handle by Emails"),
            ("inbox", "Receive in Web@LGX"),
        ],
        string="Notification",
        required=True,
        default="email",
        compute="_compute_notification_type",
        inverse="_inverse_notification_type",
        store=True,
        help=(
            "Policy on how to handle Chatter notifications:\n"
            "- Handle by Emails: notifications are sent to your email address\n"
            "- Receive in Web@LGX: notifications appear in your Web@LGX inbox"
        ),
    )
