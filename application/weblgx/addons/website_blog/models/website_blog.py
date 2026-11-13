# -*- coding: utf-8 -*-
# Part of Web@LGX. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import random

from weblgx import api, models, fields, _
from weblgx.addons.http_routing.models.ir_http import slug, unslug
from weblgx.addons.website.tools import text_from_html
from weblgx.exceptions import UserError, ValidationError
from weblgx.http import request
from weblgx.osv import expression
from weblgx.tools.json import scriptsafe as json_scriptsafe
from weblgx.tools.translate import html_translate


def blog_selected_site_domain(records):
    """Limite les listes backend au site de la société active.

    En SaaS, le site sélectionné est la société courante (une société = un site).
    ``sudo()`` (site public en élévation, PlexiPost) n'est pas restreint.
    Sur le site public, la société du contexte est déjà celle du site servi.
    """
    if records.env.su or records.env.context.get("blog_skip_website_isolation"):
        return []
    company = records.env.company
    if not company:
        return []
    return [("website_id.company_id", "=", company.id)]


def _has_request():
    try:
        return bool(request)
    except RuntimeError:
        return False


def blog_default_website_id(env):
    """Current website, or the first website of the user's companies.

    A blog record is never shared across websites. An empty ``website_id``
    would be published on every site by ``website.website_domain()``.
    """
    Website = env["website"]
    user = env.user
    superuser = env.su or user._is_superuser()
    current = Website.browse(env.context.get("website_id")) if env.context.get("website_id") else Website
    if not current and _has_request():
        current = Website.get_current_website(fallback=False)
    if current and (superuser or not current.company_id or current.company_id in user.company_ids):
        return current.id
    domain = [] if superuser else [("company_id", "in", user.company_ids.ids)]
    website = Website.sudo().search(domain, order="id", limit=1)
    if website:
        return website.id
    default = env.ref("website.default_website", raise_if_not_found=False)
    return default.id if default else False


def blog_default_blog_id(self):
    website_id = blog_default_website_id(self.env)
    domain = [("website_id", "=", website_id)] if website_id else []
    return self.env["blog.blog"].search(domain, limit=1)


def _sync_company_from_website(model):
    """Fill stored company_id from the website. Table name is one of ours."""
    table = {
        "blog.blog": "blog_blog",
        "blog.post": "blog_post",
        "blog.tag": "blog_tag",
        "blog.tag.category": "blog_tag_category",
    }[model._name]
    model.env.cr.execute(
        f"""
        UPDATE {table} AS row
           SET company_id = website.company_id
          FROM website
         WHERE row.website_id = website.id
           AND row.company_id IS DISTINCT FROM website.company_id
        """
    )


class Blog(models.Model):
    _name = 'blog.blog'
    _description = 'Blog'
    _inherit = [
        'mail.thread',
        'website.seo.metadata',
        'website.multi.mixin',
        'website.cover_properties.mixin',
        'website.searchable.mixin',
    ]
    _order = 'name'

    name = fields.Char('Blog Name', required=True, translate=True)
    subtitle = fields.Char('Blog Subtitle', translate=True)
    active = fields.Boolean('Active', default=True)
    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: blog_default_website_id(self.env),
        help="Restrict this blog to a single website.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="website_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    content = fields.Html('Content', translate=html_translate, sanitize=False)
    blog_post_ids = fields.One2many('blog.post', 'blog_id', 'Blog Posts')
    blog_post_count = fields.Integer("Posts", compute='_compute_blog_post_count')

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = blog_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )

    @api.depends('blog_post_ids')
    def _compute_blog_post_count(self):
        for record in self:
            record.blog_post_count = len(record.blog_post_ids)

    def _init_column(self, column_name):
        if column_name == "website_id":
            website_id = blog_default_website_id(self.env)
            if website_id:
                self.env.cr.execute(
                    "UPDATE blog_blog SET website_id = %s WHERE website_id IS NULL",
                    (website_id,),
                )
                return
        return super()._init_column(column_name)

    def init(self):
        _sync_company_from_website(self)
        self._blog_prepare_rule_update()

    def _blog_prepare_rule_update(self):
        """Allow the security XML to refresh rules shipped with noupdate."""
        for xmlid in ("website_blog_public", "website_blog_post_public"):
            data = self.env["ir.model.data"].sudo().search([
                ("module", "=", "website_blog"),
                ("name", "=", xmlid),
                ("model", "=", "ir.rule"),
            ], limit=1)
            if data and data.noupdate:
                data.noupdate = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("website_id"):
                website_id = blog_default_website_id(self.env)
                if not website_id:
                    raise UserError(_("A website is required to create a blog."))
                vals["website_id"] = website_id
        return super().create(vals_list)

    @api.constrains("website_id")
    def _check_tags_match_website(self):
        for blog in self:
            posts = blog.with_context(active_test=False).blog_post_ids
            mismatched = posts.tag_ids.filtered(lambda tag: tag.website_id != blog.website_id)
            if mismatched:
                raise ValidationError(_(
                    "Tags must belong to the same website as the blog (%s).",
                    blog.website_id.display_name,
                ))

    def write(self, vals):
        res = super(Blog, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a blog does it on its posts, too
            post_ids = self.env['blog.post'].with_context(active_test=False).search([
                ('blog_id', 'in', self.ids)
            ])
            for blog_post in post_ids:
                blog_post.active = vals['active']
        return res

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, parent_id=False, subtype_id=False, **kwargs):
        """ Temporary workaround to avoid spam. If someone replies on a channel
        through the 'Presentation Published' email, it should be considered as a
        note as we don't want all channel followers to be notified of this answer. """
        self.ensure_one()
        if parent_id:
            parent_message = self.env['mail.message'].sudo().browse(parent_id)
            if parent_message.subtype_id and parent_message.subtype_id == self.env.ref('website_blog.mt_blog_blog_published'):
                subtype_id = self.env.ref('mail.mt_note').id
        return super(Blog, self).message_post(parent_id=parent_id, subtype_id=subtype_id, **kwargs)

    def all_tags(self, join=False, min_limit=1):
        BlogTag = self.env['blog.tag']
        req = """
            SELECT
                p.blog_id, count(*), r.blog_tag_id
            FROM
                blog_post_blog_tag_rel r
                    join blog_post p on r.blog_post_id=p.id
            WHERE
                p.blog_id in %s
            GROUP BY
                p.blog_id,
                r.blog_tag_id
            ORDER BY
                count(*) DESC
        """
        self._cr.execute(req, [tuple(self.ids)])
        tag_by_blog = {i.id: [] for i in self}
        all_tags = set()
        for blog_id, freq, tag_id in self._cr.fetchall():
            if freq >= min_limit:
                if join:
                    all_tags.add(tag_id)
                else:
                    tag_by_blog[blog_id].append(tag_id)

        if join:
            return BlogTag.browse(all_tags)

        for blog_id in tag_by_blog:
            tag_by_blog[blog_id] = BlogTag.browse(tag_by_blog[blog_id])

        return tag_by_blog

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        search_fields = ['name']
        fetch_fields = ['id', 'name']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('subtitle')
            fetch_fields.append('subtitle')
            mapping['description'] = {'name': 'subtitle', 'type': 'text', 'match': True}
        return {
            'model': 'blog.blog',
            'base_domain': [[('website_id', '=', website.id)]],
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-rss-square',
            'order': 'name desc, id desc' if 'name desc' in order else 'name asc, id desc',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for data in results_data:
            data['url'] = '/blog/%s' % data['id']
        return results_data

class BlogTagCategory(models.Model):
    _name = 'blog.tag.category'
    _description = 'Blog Tag Category'
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: blog_default_website_id(self.env),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="website_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    tag_ids = fields.One2many('blog.tag', 'category_id', string='Tags')

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = blog_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )

    _sql_constraints = [
        ('name_uniq', 'unique (name, website_id)', "Tag category already exists for this website."),
    ]

    def _init_column(self, column_name):
        if column_name == "website_id":
            website_id = blog_default_website_id(self.env)
            if website_id:
                self.env.cr.execute(
                    "UPDATE blog_tag_category SET website_id = %s WHERE website_id IS NULL",
                    (website_id,),
                )
                return
        return super()._init_column(column_name)

    def init(self):
        _sync_company_from_website(self)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("website_id"):
                vals["website_id"] = blog_default_website_id(self.env)
        return super().create(vals_list)


class BlogTag(models.Model):
    _name = 'blog.tag'
    _description = 'Blog Tag'
    _inherit = ['website.seo.metadata']
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: blog_default_website_id(self.env),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="website_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    category_id = fields.Many2one('blog.tag.category', 'Category', index=True)
    post_ids = fields.Many2many('blog.post', string='Posts')

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = blog_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )

    _sql_constraints = [
        ('name_uniq', 'unique (name, website_id)', "Tag name already exists for this website."),
    ]

    def _init_column(self, column_name):
        if column_name == "website_id":
            website_id = blog_default_website_id(self.env)
            if website_id:
                self.env.cr.execute(
                    "UPDATE blog_tag SET website_id = %s WHERE website_id IS NULL",
                    (website_id,),
                )
                return
        return super()._init_column(column_name)

    def init(self):
        _sync_company_from_website(self)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("website_id"):
                vals["website_id"] = blog_default_website_id(self.env)
        return super().create(vals_list)

    @api.constrains("category_id", "website_id")
    def _check_category_website(self):
        for tag in self:
            if tag.category_id and tag.category_id.website_id != tag.website_id:
                raise ValidationError(_("The tag category must belong to the same website as the tag."))


class BlogPost(models.Model):
    _name = "blog.post"
    _description = "Blog Post"
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.multi.mixin',
        'website.cover_properties.mixin', 'website.searchable.mixin']
    _order = 'id DESC'
    _mail_post_access = 'read'

    def _compute_website_url(self):
        super(BlogPost, self)._compute_website_url()
        for blog_post in self:
            blog_post.website_url = "/blog/%s/%s" % (slug(blog_post.blog_id), slug(blog_post))

    def _default_content(self):
        return '''
            <p class="o_default_snippet_text">''' + _("Start writing here...") + '''</p>
        '''
    name = fields.Char('Title', required=True, translate=True, default='')
    subtitle = fields.Char('Sub Title', translate=True)
    author_id = fields.Many2one('res.partner', 'Author', default=lambda self: self.env.user.partner_id, index='btree_not_null')
    author_avatar = fields.Binary(related='author_id.image_128', string="Avatar", readonly=False)
    author_name = fields.Char(related='author_id.display_name', string="Author Name", readonly=False, store=True)
    active = fields.Boolean('Active', default=True)
    blog_id = fields.Many2one('blog.blog', 'Blog', required=True, ondelete='cascade', default=blog_default_blog_id)
    tag_ids = fields.Many2many('blog.tag', string='Tags')
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="blog_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    content = fields.Html('Content', default=_default_content, translate=html_translate, sanitize=False)
    teaser = fields.Text('Teaser', compute='_compute_teaser', inverse='_set_teaser')
    teaser_manual = fields.Text(string='Teaser Content')

    website_message_ids = fields.One2many(domain=lambda self: [
        ('model', '=', self._name),
        ('message_type', '=', 'comment'),
        '|', ('blog_comment_state', '=', False), ('blog_comment_state', '=', 'approved'),
    ])

    # creation / update stuff
    create_date = fields.Datetime('Created on', readonly=True)
    published_date = fields.Datetime('Published Date')
    post_date = fields.Datetime('Publishing date', compute='_compute_post_date', inverse='_set_post_date', store=True,
                                help="The blog post will be visible for your visitors as of this date on the website if it is set as published.")
    create_uid = fields.Many2one('res.users', 'Created by', readonly=True)
    write_date = fields.Datetime('Last Updated on', readonly=True)
    write_uid = fields.Many2one('res.users', 'Last Contributor', readonly=True)
    visits = fields.Integer('No of Views', copy=False, default=0, readonly=True)
    website_id = fields.Many2one(related='blog_id.website_id', readonly=True, store=True)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = blog_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )
    plexipost_external_id = fields.Char(
        string="PlexiPost identifier",
        copy=False,
        index=True,
        help="Identifier sent by PlexiPost. A later push with the same value updates this article.",
    )

    _sql_constraints = [
        (
            "plexipost_external_id_uniq",
            "unique(website_id, plexipost_external_id)",
            "This PlexiPost identifier is already used on this website.",
        ),
    ]

    def init(self):
        self.env.cr.execute(
            """
            UPDATE blog_post AS post
               SET website_id = blog.website_id,
                   company_id = website.company_id
              FROM blog_blog AS blog
              JOIN website ON website.id = blog.website_id
             WHERE post.blog_id = blog.id
               AND (post.website_id IS DISTINCT FROM blog.website_id
                    OR post.company_id IS DISTINCT FROM website.company_id)
            """
        )

    @api.onchange("blog_id")
    def _onchange_blog_id_clear_foreign_tags(self):
        if self.blog_id:
            self.tag_ids = self.tag_ids.filtered(lambda tag: tag.website_id == self.blog_id.website_id)

    @api.constrains("blog_id", "tag_ids")
    def _check_tag_website(self):
        for post in self:
            website = post.blog_id.website_id
            mismatched = post.tag_ids.filtered(lambda tag: tag.website_id != website)
            if mismatched:
                raise ValidationError(_(
                    "Tags must belong to the same website as the blog (%s).",
                    website.display_name,
                ))

    @api.depends('content', 'teaser_manual')
    def _compute_teaser(self):
        for blog_post in self:
            if blog_post.teaser_manual:
                blog_post.teaser = blog_post.teaser_manual
            else:
                content = text_from_html(blog_post.content, True)
                blog_post.teaser = content[:200] + '...'

    def _set_teaser(self):
        for blog_post in self:
            blog_post.teaser_manual = blog_post.teaser

    @api.depends('create_date', 'published_date')
    def _compute_post_date(self):
        for blog_post in self:
            if blog_post.published_date:
                blog_post.post_date = blog_post.published_date
            else:
                blog_post.post_date = blog_post.create_date

    def _set_post_date(self):
        for blog_post in self:
            blog_post.published_date = blog_post.post_date
            if not blog_post.published_date:
                blog_post.post_date = blog_post.create_date

    def _check_for_publication(self, vals):
        if vals.get('is_published'):
            for post in self.filtered(lambda p: p.active):
                post.blog_id.message_post_with_source(
                    'website_blog.blog_post_template_new_post',
                    subject=post.name,
                    render_values={'post': post},
                    subtype_xmlid='website_blog.mt_blog_blog_published',
                )
            return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        posts = super(BlogPost, self.with_context(mail_create_nolog=True)).create(vals_list)
        for post, vals in zip(posts, vals_list):
            post._check_for_publication(vals)
        return posts

    def write(self, vals):
        result = True
        # archiving a blog post, unpublished the blog post
        if 'active' in vals and not vals['active']:
            vals['is_published'] = False
        for post in self:
            copy_vals = dict(vals)
            published_in_vals = set(vals.keys()) & {'is_published', 'website_published'}
            if (published_in_vals and 'published_date' not in vals and
                    (not post.published_date or post.published_date <= fields.Datetime.now())):
                copy_vals['published_date'] = vals[list(published_in_vals)[0]] and fields.Datetime.now() or False
            result &= super(BlogPost, post).write(copy_vals)
        self._check_for_publication(vals)
        return result

    @api.returns('self', lambda value: value.id)
    def copy_data(self, default=None):
        self.ensure_one()
        name = _("%s (copy)", self.name)
        default = dict(default or {}, name=name)
        return super(BlogPost, self).copy_data(default)

    def _get_access_action(self, access_uid=None, force_website=False):
        """ Instead of the classic form view, redirect to the post on website
        directly if user is an employee or if the post is published. """
        self.ensure_one()
        user = self.env['res.users'].sudo().browse(access_uid) if access_uid else self.env.user
        if not force_website and user.share and not self.sudo().website_published:
            return super(BlogPost, self)._get_access_action(access_uid=access_uid, force_website=force_website)
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
            'target_type': 'public',
            'res_id': self.id,
        }

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Add access button to everyone if the document is published. """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()
        if self.website_published:
            for _group_name, _group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    def _user_can_moderate_comments(self):
        """A blog administrator is a website designer of the blog company."""
        self.ensure_one()
        user = self.env.user
        if not user or user._is_public() or user.share:
            return False
        if not user.has_group("website.group_website_designer"):
            return False
        return self.company_id.id in user.company_ids.ids

    def _pending_blog_comments(self):
        self.ensure_one()
        return self.env["mail.message"].sudo().search([
            ("model", "=", "blog.post"),
            ("res_id", "=", self.id),
            ("message_type", "=", "comment"),
            ("blog_comment_state", "=", "pending"),
        ], order="date asc, id asc")

    def _get_message_create_valid_field_names(self):
        return super()._get_message_create_valid_field_names() | {"blog_comment_state"}

    def message_post(self, **kwargs):
        if (
            self.env.context.get("blog_comment_from_portal")
            and kwargs.get("message_type", "notification") == "comment"
            and kwargs.get("subtype_xmlid", "mail.mt_comment") == "mail.mt_comment"
            and "blog_comment_state" not in kwargs
        ):
            kwargs["blog_comment_state"] = (
                "approved" if self._user_can_moderate_comments() else "pending"
            )
        return super().message_post(**kwargs)

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        if message.blog_comment_state == "pending":
            return
        return super()._notify_thread(message, msg_vals=msg_vals, **kwargs)

    def _notify_thread_by_inbox(self, message, recipients_data, msg_vals=False, **kwargs):
        """ Override to avoid keeping all notified recipients of a comment.
        We avoid tracking needaction on post comments. Only emails should be
        sufficient. """
        if msg_vals is None:
            msg_vals = {}
        if msg_vals.get('message_type', message.message_type) == 'comment':
            return
        return super(BlogPost, self)._notify_thread_by_inbox(message, recipients_data, msg_vals=msg_vals, **kwargs)

    def _default_website_meta(self):
        res = super(BlogPost, self)._default_website_meta()
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.subtitle
        res['default_opengraph']['og:type'] = 'article'
        res['default_opengraph']['article:published_time'] = self.post_date
        res['default_opengraph']['article:modified_time'] = self.write_date
        res['default_opengraph']['article:tag'] = self.tag_ids.mapped('name')
        # background-image might contain single quotes eg `url('/my/url')`
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = json_scriptsafe.loads(self.cover_properties).get('background-image', 'none')[4:-1].strip("'")
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_meta_description'] = self.subtitle
        return res

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        with_date = options['displayDetail']
        blog = options.get('blog')
        tags = options.get('tag')
        date_begin = options.get('date_begin')
        date_end = options.get('date_end')
        state = options.get('state')
        domain = [[('website_id', '=', website.id)]]
        if blog:
            domain.append([('blog_id', '=', unslug(blog)[1])])
        if tags:
            active_tag_ids = [unslug(tag)[1] for tag in tags.split(',')] or []
            if active_tag_ids:
                domain.append([('tag_ids', 'in', active_tag_ids)])
        if date_begin and date_end:
            domain.append([("post_date", ">=", date_begin), ("post_date", "<=", date_end)])
        if self.env.user.has_group('website.group_website_designer'):
            if state == "published":
                domain.append([("website_published", "=", True), ("post_date", "<=", fields.Datetime.now())])
            elif state == "unpublished":
                domain.append(['|', ("website_published", "=", False), ("post_date", ">", fields.Datetime.now())])
        else:
            domain.append([("post_date", "<=", fields.Datetime.now())])
        search_fields = ['name', 'author_name']
        def search_in_tags(env, search_term):
            tag_domain = [('name', 'ilike', search_term), ('website_id', '=', website.id)]
            tags_like_search = env['blog.tag'].search(tag_domain)
            return [('tag_ids', 'in', tags_like_search.ids)]
        fetch_fields = ['name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('content')
            fetch_fields.append('content')
            mapping['description'] = {'name': 'content', 'type': 'text', 'html': True, 'match': True}
        if with_date:
            fetch_fields.append('published_date')
            mapping['detail'] = {'name': 'published_date', 'type': 'date'}
        return {
            'model': 'blog.post',
            'base_domain': domain,
            'search_fields': search_fields,
            'search_extra': search_in_tags,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-rss',
        }
