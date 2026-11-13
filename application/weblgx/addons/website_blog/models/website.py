# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

import hmac
import secrets

from weblgx import _, api, fields, models
from weblgx.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = "website"

    plexipost_client_id = fields.Char(
        string="Client ID",
        copy=False,
        groups="website.group_website_designer",
    )
    plexipost_client_secret = fields.Char(
        string="Secret",
        copy=False,
        groups="website.group_website_designer",
    )
    plexipost_blog_id = fields.Many2one(
        "blog.blog",
        string="Blog",
        copy=False,
        domain="[('website_id', '=', id)]",
        groups="website.group_website_designer",
        help="Articles pushed by PlexiPost are created in this blog.",
    )
    plexipost_receiver_url = fields.Char(
        string="Receiver URL",
        compute="_compute_plexipost_receiver_url",
        groups="website.group_website_designer",
        help="Address to enter in PlexiPost for this website.",
    )

    _sql_constraints = [
        (
            "plexipost_client_id_uniq",
            "unique(plexipost_client_id)",
            "This PlexiPost Client ID is already used by another website.",
        ),
    ]

    @api.depends("domain")
    def _compute_plexipost_receiver_url(self):
        for website in self:
            base = (website.domain or website.get_base_url() or "").rstrip("/")
            website.plexipost_receiver_url = "%s/blog/plexipost/receive" % base

    def action_plexipost_generate_credentials(self):
        for website in self:
            website.write({
                "plexipost_client_id": "lgx_%s" % secrets.token_hex(12),
                "plexipost_client_secret": secrets.token_urlsafe(32),
            })
        return True

    def _plexipost_secret_matches(self, secret):
        self.ensure_one()
        stored = self.sudo().plexipost_client_secret or ""
        candidate = secret or ""
        if not stored or not candidate:
            return False
        return hmac.compare_digest(stored, candidate)

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Blog'), url_for('/blog'), 'website_blog'))
        return suggested_controllers

    def configurator_set_menu_links(self, menu_company, module_data):
        blogs = module_data.get('#blog', [])
        for idx, blog in enumerate(blogs):
            new_blog = self.env['blog.blog'].create({
                'name': blog['name'],
                'website_id': self.id,
            })
            blog_menu_values = {
                'name': blog['name'],
                'url': '/blog/%s' % new_blog.id,
                'sequence': blog['sequence'],
                'parent_id': menu_company.id if menu_company else self.menu_id.id,
                'website_id': self.id,
            }
            if idx == 0:
                blog_menu = self.env['website.menu'].search([('url', '=', '/blog'), ('website_id', '=', self.id)])
                blog_menu.write(blog_menu_values)
            else:
                self.env['website.menu'].create(blog_menu_values)
        super().configurator_set_menu_links(menu_company, module_data)

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['blogs', 'blogs_only', 'all']:
            result.append(self.env['blog.blog']._search_get_detail(self, order, options))
        if search_type in ['blogs', 'blog_posts_only', 'all']:
            result.append(self.env['blog.post']._search_get_detail(self, order, options))
        return result
