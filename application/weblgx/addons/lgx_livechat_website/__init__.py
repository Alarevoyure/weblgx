# -*- coding: utf-8 -*-

from . import models

from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {})
    env["im_livechat.channel"]._sync_all_website_links()
