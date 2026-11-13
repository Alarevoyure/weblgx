# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

from weblgx import models
from weblgx.addons.calendar.populate import data
from weblgx.tools import populate


class Alarm(models.Model):
    _inherit = 'calendar.alarm'
    _populate_sizes = {'small': 3, 'medium': 10, 'large': 30}

    def _populate_factories(self):
        def get_name(values, counter, **kwargs):
            return f"{str.capitalize(values['alarm_type'])} - {values['duration']} {values['interval']} (#{counter})."

        return [
            *((field_name, populate.iterate(*zip(*data.calendar_alarm[field_name].items())))
              for field_name in ["alarm_type", "duration", "interval"]),
            ('name', populate.compute(get_name)),
        ]
