# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from psycopg2 import sql

import hashlib
import pytz
import threading

from odoo import fields, models, api, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.website.tools import get_base_domain
from odoo.exceptions import UserError
from odoo.tools import split_every
from odoo.tools.misc import _format_time_ago
from odoo.http import request
from odoo.osv import expression


def visitor_selected_site_domain(records):
    """Limite Analyse → Visiteurs au site de la société active.

    Un visiteur sans ``website_id`` est exclu. ``sudo()`` (suivi des pages,
    cron) n'est pas restreint. Sur le site public, la société du contexte
    est déjà celle du site servi.
    """
    if records.env.su or records.env.context.get("visitor_skip_website_isolation"):
        return []
    company = records.env.company
    if not company:
        return []
    if records._name == "website.track":
        return [("visitor_id.website_id.company_id", "=", company.id)]
    return [("website_id.company_id", "=", company.id)]


class WebsiteTrack(models.Model):
    _name = 'website.track'
    _description = 'Visited Pages'
    _order = 'visit_datetime DESC'
    _log_access = False

    visitor_id = fields.Many2one('website.visitor', ondelete="cascade", index=True, required=True, readonly=True)
    page_id = fields.Many2one('website.page', index=True, ondelete='cascade', readonly=True)
    url = fields.Text('Url', index=True)
    visit_datetime = fields.Datetime('Visit Date', default=fields.Datetime.now, required=True, readonly=True)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = visitor_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _description = 'Website Visitor'
    _order = 'id DESC'

    def _get_access_token(self):
        """ Either the user's partner.id or a hash. """
        if not request:
            raise ValueError("Visitors can only be created through the frontend.")

        if not request.env.user._is_public():
            return request.env.user.partner_id.id

        msg = repr((
            request.httprequest.remote_addr,
            request.httprequest.environ.get('HTTP_USER_AGENT'),
            request.session.sid,
        )).encode('utf-8')
        # Keep same length (32) as before, it will ease the migration without
        # any real downside
        return hashlib.sha1(msg).hexdigest()[:32]

    name = fields.Char('Name', related='partner_id.name')
    access_token = fields.Char(required=True, default=_get_access_token, copy=False)
    website_id = fields.Many2one('website', "Website", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Contact", help="Partner of the last logged in user.", compute='_compute_partner_id', store=True, index='btree_not_null')
    partner_image = fields.Binary(related='partner_id.image_1920')

    # localisation and info
    country_id = fields.Many2one('res.country', 'Country', readonly=True)
    country_flag = fields.Char(related="country_id.image_url", string="Country Flag")
    lang_id = fields.Many2one('res.lang', string='Language', help="Language from the website when visitor has been created")
    timezone = fields.Selection(_tz_get, string='Timezone')
    email = fields.Char(string='Email', compute='_compute_email_phone', compute_sudo=True)
    mobile = fields.Char(string='Mobile', compute='_compute_email_phone', compute_sudo=True)

    # Visit fields
    visit_count = fields.Integer('# Visits', default=1, readonly=True, help="A new visit is considered if last connection was more than 8 hours ago.")
    website_track_ids = fields.One2many('website.track', 'visitor_id', string='Visited Pages History', readonly=True)
    visitor_page_count = fields.Integer('Page Views', compute="_compute_page_statistics", help="Total number of visits on tracked pages")
    page_ids = fields.Many2many('website.page', string="Visited Pages", compute="_compute_page_statistics", groups="website.group_website_designer", search="_search_page_ids")
    page_count = fields.Integer('# Visited Pages', compute="_compute_page_statistics", help="Total number of tracked page visited")
    last_visited_page_id = fields.Many2one('website.page', string="Last Visited Page", compute="_compute_last_visited_page_id")

    # Time fields
    create_date = fields.Datetime('First Connection', readonly=True)
    last_connection_datetime = fields.Datetime('Last Connection', default=fields.Datetime.now, help="Last page view date", readonly=True)
    time_since_last_action = fields.Char('Last action', compute="_compute_time_statistics", help='Time since last page view. E.g.: 2 minutes ago')
    is_connected = fields.Boolean('Is connected?', compute='_compute_time_statistics', help='A visitor is considered as connected if his last page view was within the last 5 minutes.')

    _sql_constraints = [
        ('access_token_unique', 'unique(access_token)', 'Access token should be unique.'),
    ]

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = visitor_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )

    @api.depends('partner_id')
    def _compute_display_name(self):
        for record in self:
            # Accessing name of partner through sudo to avoid infringing
            # record rule if partner belongs to another company.
            record.display_name = record.partner_id.sudo().name or _('Website Visitor #%s', record.id)

    @api.depends('access_token')
    def _compute_partner_id(self):
        # The browse in the loop is fine, there is no SQL Query on partner here
        for visitor in self:
            # If the access_token is not a 32 length hexa string, it means that
            # the visitor is linked to a logged in user, in which case its
            # partner_id is used instead as the token.
            partner_id = len(visitor.access_token) != 32 and int(visitor.access_token)
            visitor.partner_id = self.env['res.partner'].browse(partner_id)

    @api.depends('partner_id.email_normalized', 'partner_id.mobile', 'partner_id.phone')
    def _compute_email_phone(self):
        results = self.env['res.partner'].search_read(
            [('id', 'in', self.partner_id.ids)],
            ['id', 'email_normalized', 'mobile', 'phone'],
        )
        mapped_data = {
            result['id']: {
                'email_normalized': result['email_normalized'],
                'mobile': result['mobile'] if result['mobile'] else result['phone']
            } for result in results
        }

        for visitor in self:
            visitor.email = mapped_data.get(visitor.partner_id.id, {}).get('email_normalized')
            visitor.mobile = mapped_data.get(visitor.partner_id.id, {}).get('mobile')

    @api.depends('website_track_ids')
    def _compute_page_statistics(self):
        results = self.env['website.track']._read_group(
            [('visitor_id', 'in', self.ids), ('url', '!=', False)], ['visitor_id', 'page_id'], ['__count'])
        mapped_data = {}
        for visitor, page, count in results:
            visitor_info = mapped_data.get(visitor.id, {'page_count': 0, 'visitor_page_count': 0, 'page_ids': set()})
            visitor_info['visitor_page_count'] += count
            visitor_info['page_count'] += 1
            if page:
                visitor_info['page_ids'].add(page.id)
            mapped_data[visitor.id] = visitor_info

        for visitor in self:
            visitor_info = mapped_data.get(visitor.id, {'page_count': 0, 'visitor_page_count': 0, 'page_ids': set()})
            visitor.page_ids = [(6, 0, visitor_info['page_ids'])]
            visitor.visitor_page_count = visitor_info['visitor_page_count']
            visitor.page_count = visitor_info['page_count']

    def _search_page_ids(self, operator, value):
        if operator not in ('like', 'ilike', 'not like', 'not ilike', '=like', '=ilike', '=', '!='):
            raise ValueError(_('This operator is not supported'))
        return [('website_track_ids.page_id.name', operator, value)]

    @api.depends('website_track_ids.page_id')
    def _compute_last_visited_page_id(self):
        results = self.env['website.track']._read_group(
            [('visitor_id', 'in', self.ids), ('page_id', '!=', False)],
            ['visitor_id', 'page_id'],
            order='visit_datetime:max')
        mapped_data = {visitor.id: page.id for visitor, page in results}
        for visitor in self:
            visitor.last_visited_page_id = mapped_data.get(visitor.id, False)

    @api.depends('last_connection_datetime')
    def _compute_time_statistics(self):
        for visitor in self:
            visitor.time_since_last_action = _format_time_ago(self.env, (datetime.now() - visitor.last_connection_datetime))
            visitor.is_connected = (datetime.now() - visitor.last_connection_datetime) < timedelta(minutes=5)

    def _check_for_message_composer(self):
        """ Purpose of this method is to actualize visitor model prior to contacting
        him. Used notably for inheritance purpose, when dealing with leads that
        could update the visitor model. """
        return bool(self.partner_id and self.partner_id.email)

    def _prepare_message_composer_context(self):
        return {
            'default_model': 'res.partner',
            'default_res_ids': self.partner_id.ids,
            'default_partner_ids': [self.partner_id.id],
        }

    def action_send_mail(self):
        self.ensure_one()
        if not self._check_for_message_composer():
            raise UserError(_("There are no contact and/or no email linked to this visitor."))
        visitor_composer_ctx = self._prepare_message_composer_context()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        compose_ctx = dict(
            default_composition_mode='comment',
        )
        compose_ctx.update(**visitor_composer_ctx)
        return {
            'name': _('Contact Visitor'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': compose_ctx,
        }

    def _upsert_visitor(self, access_token, force_track_values=None):
        """ Based on the given `access_token`, either create or return the
        related visitor if exists, through a single raw SQL UPSERT Query.

        It will also create a tracking record if requested, in the same query.

        :param access_token: token to be used to upsert the visitor
        :param force_track_values: an optional dict to create a track at the
            same time.
        :return: a tuple containing the visitor id and the upsert result (either
            `inserted` or `updated).
        """
        create_values = {
            'access_token': access_token,
            'lang_id': request.lang.id,
            # Note that it's possible for the GEOIP database to return a country
            # code which is unknown in Odoo
            'country_code': request.geoip.country_code,
            'website_id': request.website.id,
            'timezone': self._get_visitor_timezone() or None,
            'write_uid': self.env.uid,
            'create_uid': self.env.uid,
            # If the access_token is not a 32 length hexa string, it means that the
            # visitor is linked to a logged in user, in which case its partner_id is
            # used instead as the token.
            'partner_id': None if len(str(access_token)) == 32 else access_token,
        }
        query = """
            INSERT INTO website_visitor (
                partner_id, access_token, last_connection_datetime, visit_count, lang_id,
                website_id, timezone, write_uid, create_uid, write_date, create_date, country_id)
            VALUES (
                %(partner_id)s, %(access_token)s, now() at time zone 'UTC', 1, %(lang_id)s,
                %(website_id)s, %(timezone)s, %(create_uid)s, %(write_uid)s,
                now() at time zone 'UTC', now() at time zone 'UTC', (
                    SELECT id FROM res_country WHERE code = %(country_code)s
                )
            )
            ON CONFLICT (access_token)
            DO UPDATE SET
                last_connection_datetime=excluded.last_connection_datetime,
                country_id = COALESCE(website_visitor.country_id, excluded.country_id),
                visit_count = CASE WHEN website_visitor.last_connection_datetime < NOW() AT TIME ZONE 'UTC' - INTERVAL '8 hours'
                                    THEN website_visitor.visit_count + 1
                                    ELSE website_visitor.visit_count
                                END
            RETURNING id, CASE WHEN create_date = now() at time zone 'UTC' THEN 'inserted' ELSE 'updated' END AS upsert
        """

        if force_track_values:
            create_values['url'] = force_track_values['url']
            create_values['page_id'] = force_track_values.get('page_id')
            query = sql.SQL("""
                WITH visitor AS (
                    {query}, %(url)s AS url, %(page_id)s AS page_id
                ), track AS (
                    INSERT INTO website_track (visitor_id, url, page_id, visit_datetime)
                    SELECT id, url, page_id::integer, now() at time zone 'UTC' FROM visitor
                )
                SELECT id, upsert from visitor;
            """).format(query=sql.SQL(query))

        self.env.cr.execute(query, create_values)
        return self.env.cr.fetchone()

    def _get_visitor_from_request(self, force_create=False, force_track_values=None):
        """ Return the visitor as sudo from the request.

        :param bool force_create: force a visitor creation if no visitor exists
        :param force_track_values: an optional dict to create a track at the
            same time.
        :return: the website visitor if exists or forced, empty recordset
                 otherwise.
        """

        # This function can be called in json with mobile app.
        # In case of mobile app, no uid is set on the jsonRequest env.
        # In case of multi db, _env is None on request, and request.env unbound.
        if not (request and request.env and request.env.uid):
            return None

        Visitor = self.env['website.visitor'].sudo()
        visitor = Visitor
        access_token = self._get_access_token()

        if force_create:
            visitor_id, _ = self._upsert_visitor(access_token, force_track_values)
            visitor = Visitor.browse(visitor_id)
        else:
            visitor = Visitor.search([('access_token', '=', access_token)])

        if not force_create and visitor and not visitor.timezone:
            tz = self._get_visitor_timezone()
            if tz:
                visitor._update_visitor_timezone(tz)

        return visitor

    def _handle_webpage_dispatch(self, website_page):
        """ Create a website.visitor if the http request object is a tracked
        website.page or a tracked ir.ui.view.
        Since this method is only called on tracked elements, the
        last_connection_datetime might not be accurate as the visitor could have
        been visiting only untracked page during his last visit."""

        url = request.httprequest.url
        website_track_values = {'url': url}
        if website_page:
            website_track_values['page_id'] = website_page.id
        self._get_visitor_from_request(force_create=True, force_track_values=website_track_values)

    def _add_tracking(self, domain, website_track_values):
        """ Add the track and update the visitor"""
        domain = expression.AND([domain, [('visitor_id', '=', self.id)]])
        last_view = self.env['website.track'].sudo().search(domain, limit=1)
        if not last_view or last_view.visit_datetime < datetime.now() - timedelta(minutes=30):
            website_track_values['visitor_id'] = self.id
            self.env['website.track'].create(website_track_values)
        self._update_visitor_last_visit()

    def _merge_visitor(self, target):
        """ Merge an anonymous visitor data to a partner visitor then unlink
        that anonymous visitor.
        Purpose is to try to aggregate as much sub-records (tracked pages,
        leads, ...) as possible.
        It is especially useful to aggregate data from the same user on
        different devices.

        This method is meant to be overridden for other modules to merge their
        own anonymous visitor data to the partner visitor before unlink.

        This method is only called after the user logs in.

        :param target: main visitor, target of link process;
        """
        if not target.partner_id:
            raise ValueError("The `target` visitor should be linked to a partner.")
        self.website_track_ids.visitor_id = target.id
        self.unlink()

    def _cron_unlink_old_visitors(self, batch_size=1000, limit=None):
        """ Unlink inactive visitors (see '_inactive_visitors_domain' for
        details).

        Visitors were previously archived but we came to the conclusion that
        archived visitors have very little value and bloat the database for no
        reason. """
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        visitor_model = self.env['website.visitor']
        for inactive_visitors_batch in split_every(
            batch_size,
            visitor_model.sudo().search(self._inactive_visitors_domain(), limit=limit).ids,
            visitor_model.browse,
        ):
            inactive_visitors_batch.unlink()
            if auto_commit:
                self.env.cr.commit()

    def _inactive_visitors_domain(self):
        """ This method defines the domain of visitors that can be cleaned. By
        default visitors not linked to any partner and not active for
        'website.visitor.live.days' days (default being 60) are considered as
        inactive.

        This method is meant to be overridden by sub-modules to further refine
        inactivity conditions. """

        delay_days = int(self.env['ir.config_parameter'].sudo().get_param('website.visitor.live.days', 60))
        deadline = datetime.now() - timedelta(days=delay_days)
        return [('last_connection_datetime', '<', deadline), ('partner_id', '=', False)]

    def _update_visitor_timezone(self, timezone):
        """ We need to do this part here to avoid concurrent updates error. """
        query = """
            UPDATE website_visitor
            SET timezone = %s
            WHERE id IN (
                SELECT id FROM website_visitor WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (timezone, self.id))

    def _update_visitor_last_visit(self):
        date_now = datetime.now()
        query = "UPDATE website_visitor SET "
        if self.last_connection_datetime < (date_now - timedelta(hours=8)):
            query += "visit_count = visit_count + 1,"
        query += """
            last_connection_datetime = %s
            WHERE id IN (
                SELECT id FROM website_visitor WHERE id = %s
                FOR NO KEY UPDATE SKIP LOCKED
            )
        """
        self.env.cr.execute(query, (date_now, self.id), log_exceptions=False)

    def _get_visitor_timezone(self):
        tz = request.httprequest.cookies.get('tz') if request else None
        if tz in pytz.all_timezones:
            return tz
        elif not self.env.user._is_public():
            return self.env.user.tz
        else:
            return None

    @api.model
    def get_site_analytics(self, days=30):
        """Statistiques de visite du site de la société active.

        Une visite regroupe les pages vues d'un même visiteur séparées de
        moins de 30 minutes. La durée est le temps entre la première et la
        dernière page d'une visite qui en compte plusieurs.

        Les comptes connectés (administrateur, utilisateur interne ou portail)
        ont un contact. Leurs visites sont écartées. Seules les adresses du
        domaine configuré du site sont comptées, avec ou sans ``www``.
        """
        self.check_access_rights('read')
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 30
        if days not in (7, 30, 90):
            days = 30

        website = self.env['website'].search(
            [('company_id', '=', self.env.company.id)],
            limit=1,
            order='sequence, id',
        )
        empty = {
            'website_name': website.name or False,
            'days': days,
            'online': 0,
            'visitors': 0,
            'page_views': 0,
            'sessions': 0,
            'pages_per_session': 0,
            'avg_duration': '—',
            'single_page_rate': 0,
            'new_visitors': 0,
            'returning_visitors': 0,
            'series': {
                'labels': [],
                'visitors': [],
                'page_views': [],
                'multi_visitors': [],
                'multi_page_views': [],
            },
            'pages': [],
            'countries': [],
            'hours': [0] * 24,
            'landings': [],
            'flows': [],
            'multi': self._empty_multi(),
            'previous': self._empty_previous_period(),
        }
        if not website:
            return empty

        tzname = self.env.user.tz or 'Europe/Paris'
        if tzname not in pytz.all_timezones:
            tzname = 'Europe/Paris'
        tz = pytz.timezone(tzname)
        now = datetime.now(tz)
        start_day = (now - timedelta(days=days - 1)).date()
        start_dt = tz.localize(datetime.combine(start_day, datetime.min.time())).astimezone(pytz.UTC).replace(tzinfo=None)

        cr = self.env.cr
        # partner_id is set only when the visitor was logged in.
        public_visitor = "v.partner_id IS NULL"
        # Exact host of the website URL. Scheme and port are ignored.
        # www.loegaux.fr does not include loegaux.fr, nor an IP address.
        raw_host = get_base_domain(website.domain or '', strip_www=False).split(':')[0].lower()
        try:
            site_host = raw_host.encode('idna').decode('ascii')
        except UnicodeError:
            site_host = raw_host
        on_site = """
            lower(split_part(substring(t.url from '://([^/?#]+)'), ':', 1)) = %s
        """
        cr.execute("""
            SELECT (t.visit_datetime AT TIME ZONE 'UTC' AT TIME ZONE %s)::date AS day,
                   COUNT(*) AS page_views,
                   COUNT(DISTINCT t.visitor_id) AS visitors
              FROM website_track t
              JOIN website_visitor v ON v.id = t.visitor_id
             WHERE v.website_id = %s
               AND t.visit_datetime >= %s
               AND """ + public_visitor + """
               AND """ + on_site + """
          GROUP BY 1
        """, (tzname, website.id, start_dt, site_host))
        by_day = {row['day']: row for row in cr.dictfetchall()}

        labels, visitors_series, views_series = [], [], []
        for offset in range(days):
            day = start_day + timedelta(days=offset)
            row = by_day.get(day)
            labels.append(day.strftime('%d/%m'))
            visitors_series.append(row['visitors'] if row else 0)
            views_series.append(row['page_views'] if row else 0)

        cr.execute("""
            WITH several AS (
                SELECT t.visitor_id
                  FROM website_track t
                  JOIN website_visitor v ON v.id = t.visitor_id
                 WHERE v.website_id = %s
                   AND t.visit_datetime >= %s
                   AND """ + public_visitor + """
                   AND """ + on_site + """
              GROUP BY t.visitor_id
                HAVING COUNT(*) > 1
            )
            SELECT (t.visit_datetime AT TIME ZONE 'UTC' AT TIME ZONE %s)::date AS day,
                   COUNT(DISTINCT t.visitor_id) AS visitors,
                   COUNT(*) AS page_views
              FROM website_track t
              JOIN website_visitor v ON v.id = t.visitor_id
              JOIN several s ON s.visitor_id = t.visitor_id
             WHERE v.website_id = %s
               AND t.visit_datetime >= %s
               AND """ + public_visitor + """
               AND """ + on_site + """
          GROUP BY 1
        """, (website.id, start_dt, site_host, tzname, website.id, start_dt, site_host))
        several_by_day = {row['day']: row for row in cr.dictfetchall()}
        multi_visitors, multi_views = [], []
        for offset in range(days):
            row = several_by_day.get(start_day + timedelta(days=offset))
            multi_visitors.append(row['visitors'] if row else 0)
            multi_views.append(row['page_views'] if row else 0)

        cr.execute("""
            WITH ordered AS (
                SELECT t.visitor_id,
                       t.id,
                       t.visit_datetime,
                       LAG(t.visit_datetime) OVER (
                           PARTITION BY t.visitor_id ORDER BY t.visit_datetime, t.id
                       ) AS prev
                  FROM website_track t
                  JOIN website_visitor v ON v.id = t.visitor_id
                 WHERE v.website_id = %s
                   AND t.visit_datetime >= %s
                   AND """ + public_visitor + """
                   AND """ + on_site + """
            ), marked AS (
                SELECT visitor_id,
                       visit_datetime,
                       SUM(CASE
                           WHEN prev IS NULL OR visit_datetime - prev > INTERVAL '30 minutes'
                           THEN 1 ELSE 0 END) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                       ) AS session_n
                  FROM ordered
            ), sessions AS (
                SELECT visitor_id,
                       session_n,
                       MIN(visit_datetime) AS started,
                       MAX(visit_datetime) AS ended,
                       COUNT(*) AS pages
                  FROM marked
              GROUP BY visitor_id, session_n
            )
            SELECT COUNT(*) AS sessions,
                   COUNT(*) FILTER (WHERE pages = 1) AS single_page,
                   AVG(EXTRACT(EPOCH FROM (ended - started))) FILTER (WHERE pages > 1) AS avg_seconds,
                   COALESCE(SUM(pages), 0) AS page_views,
                   COUNT(*) FILTER (WHERE pages > 1) AS multi_sessions,
                   COUNT(DISTINCT visitor_id) FILTER (WHERE pages > 1) AS multi_visitors,
                   COALESCE(SUM(pages) FILTER (WHERE pages > 1), 0) AS multi_page_views
              FROM sessions
        """, (website.id, start_dt, site_host))
        sessions = cr.dictfetchone()

        cr.execute("""
            SELECT COUNT(*) FILTER (WHERE v.create_date >= %s) AS new_visitors,
                   COUNT(*) FILTER (WHERE v.create_date < %s) AS returning_visitors
              FROM website_visitor v
             WHERE v.website_id = %s
               AND """ + public_visitor + """
               AND EXISTS (
                    SELECT 1 FROM website_track t
                     WHERE t.visitor_id = v.id
                       AND t.visit_datetime >= %s
                       AND """ + on_site + """
               )
        """, (start_dt, start_dt, website.id, start_dt, site_host))
        cohort = cr.dictfetchone()

        cr.execute("""
            SELECT COALESCE(NULLIF(page.url, ''), NULLIF(path.path, ''), '/') AS label,
                   COUNT(*) AS views,
                   COUNT(DISTINCT t.visitor_id) AS visitors
              FROM website_track t
              JOIN website_visitor v ON v.id = t.visitor_id
              LEFT JOIN website_page page ON page.id = t.page_id
              CROSS JOIN LATERAL (
                    SELECT regexp_replace(split_part(t.url, '?', 1), '^https?://[^/]+', '') AS path
              ) path
             WHERE v.website_id = %s
               AND t.visit_datetime >= %s
               AND t.url IS NOT NULL
               AND """ + public_visitor + """
               AND """ + on_site + """
          GROUP BY 1
          ORDER BY views DESC, visitors DESC
             LIMIT 8
        """, (website.id, start_dt, site_host))
        pages = cr.dictfetchall()

        cr.execute("""
            SELECT COALESCE(c.name->>'fr_FR', c.name->>'en_US', 'Non renseigné') AS label,
                   COUNT(DISTINCT v.id) AS visitors
              FROM website_visitor v
              JOIN website_track t ON t.visitor_id = v.id AND t.visit_datetime >= %s
              LEFT JOIN res_country c ON c.id = v.country_id
             WHERE v.website_id = %s
               AND """ + public_visitor + """
               AND """ + on_site + """
          GROUP BY 1
          ORDER BY visitors DESC
             LIMIT 6
        """, (start_dt, website.id, site_host))
        countries = [
            row for row in cr.dictfetchall()
            if row['label'] != 'Non renseigné'
        ]

        cr.execute("""
            SELECT COUNT(DISTINCT v.id)
              FROM website_visitor v
              JOIN website_track t ON t.visitor_id = v.id
             WHERE v.website_id = %s
               AND t.visit_datetime >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '5 minutes'
               AND """ + public_visitor + """
               AND """ + on_site + """
        """, (website.id, site_host))
        online = cr.fetchone()[0]

        now_utc = datetime.now(pytz.UTC).replace(tzinfo=None)
        elapsed = now_utc - start_dt
        if elapsed.total_seconds() < 60:
            elapsed = timedelta(days=days)
        prev_start = start_dt - elapsed
        cr.execute("""
            SELECT COUNT(DISTINCT v.id)
              FROM website_visitor v
             WHERE v.website_id = %s
               AND """ + public_visitor + """
               AND EXISTS (
                    SELECT 1 FROM website_track t
                     WHERE t.visitor_id = v.id
                       AND t.visit_datetime >= %s
                       AND t.visit_datetime < %s
                       AND """ + on_site + """
               )
        """, (website.id, prev_start, start_dt, site_host))
        previous_visitors = cr.fetchone()[0]
        cr.execute("""
            WITH ordered AS (
                SELECT t.visitor_id,
                       t.id,
                       t.visit_datetime,
                       LAG(t.visit_datetime) OVER (
                           PARTITION BY t.visitor_id ORDER BY t.visit_datetime, t.id
                       ) AS prev
                  FROM website_track t
                  JOIN website_visitor v ON v.id = t.visitor_id
                 WHERE v.website_id = %s
                   AND t.visit_datetime >= %s
                   AND t.visit_datetime < %s
                   AND """ + public_visitor + """
                   AND """ + on_site + """
            ), marked AS (
                SELECT visitor_id,
                       visit_datetime,
                       SUM(CASE
                           WHEN prev IS NULL OR visit_datetime - prev > INTERVAL '30 minutes'
                           THEN 1 ELSE 0 END) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                       ) AS session_n
                  FROM ordered
            ), grouped AS (
                SELECT visitor_id,
                       session_n,
                       MIN(visit_datetime) AS started,
                       MAX(visit_datetime) AS ended,
                       COUNT(*) AS pages
                  FROM marked
              GROUP BY visitor_id, session_n
            )
            SELECT COUNT(*) AS sessions,
                   AVG(EXTRACT(EPOCH FROM (ended - started))) FILTER (WHERE pages > 1) AS avg_seconds,
                   COALESCE(SUM(pages), 0) AS page_views
              FROM grouped
        """, (website.id, prev_start, start_dt, site_host))
        previous_sessions = cr.dictfetchone()

        cr.execute("""
            WITH base AS (
                SELECT t.visitor_id,
                       t.id,
                       t.visit_datetime,
                       COALESCE(NULLIF(page.url, ''), NULLIF(path.path, ''), '/') AS label
                  FROM website_track t
                  JOIN website_visitor v ON v.id = t.visitor_id
                  LEFT JOIN website_page page ON page.id = t.page_id
                  CROSS JOIN LATERAL (
                        SELECT regexp_replace(split_part(t.url, '?', 1), '^https?://[^/]+', '') AS path
                  ) path
                 WHERE v.website_id = %s
                   AND t.visit_datetime >= %s
                   AND t.url IS NOT NULL
                   AND """ + public_visitor + """
                   AND """ + on_site + """
            ), ordered AS (
                SELECT base.*,
                       LAG(visit_datetime) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                       ) AS prev
                  FROM base
            ), marked AS (
                SELECT ordered.*,
                       SUM(CASE
                           WHEN prev IS NULL OR visit_datetime - prev > INTERVAL '30 minutes'
                           THEN 1 ELSE 0 END) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                       ) AS session_n
                  FROM ordered
            ), multi AS (
                SELECT visitor_id, session_n
                  FROM marked
              GROUP BY visitor_id, session_n
                HAVING COUNT(*) > 1
            ), arrivals AS (
                SELECT m.visitor_id,
                       m.session_n,
                       MIN(m.visit_datetime) AS started,
                       (ARRAY_AGG(m.label ORDER BY m.visit_datetime, m.id))[1] AS landing
                  FROM marked m
                  JOIN multi u
                    ON u.visitor_id = m.visitor_id
                   AND u.session_n = m.session_n
              GROUP BY m.visitor_id, m.session_n
            )
            SELECT EXTRACT(HOUR FROM (started AT TIME ZONE 'UTC' AT TIME ZONE %s))::int AS hour,
                   COUNT(*) AS visits
              FROM arrivals
          GROUP BY 1
        """, (website.id, start_dt, site_host, tzname))
        hours = [0] * 24
        for row in cr.dictfetchall():
            hours[int(row['hour'])] = row['visits']

        cr.execute("""
            WITH base AS (
                SELECT t.visitor_id,
                       t.id,
                       t.visit_datetime,
                       COALESCE(NULLIF(page.url, ''), NULLIF(path.path, ''), '/') AS label
                  FROM website_track t
                  JOIN website_visitor v ON v.id = t.visitor_id
                  LEFT JOIN website_page page ON page.id = t.page_id
                  CROSS JOIN LATERAL (
                        SELECT regexp_replace(split_part(t.url, '?', 1), '^https?://[^/]+', '') AS path
                  ) path
                 WHERE v.website_id = %s
                   AND t.visit_datetime >= %s
                   AND t.url IS NOT NULL
                   AND """ + public_visitor + """
                   AND """ + on_site + """
            ), ordered AS (
                SELECT base.*,
                       LAG(visit_datetime) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                       ) AS prev
                  FROM base
            ), marked AS (
                SELECT ordered.*,
                       SUM(CASE
                           WHEN prev IS NULL OR visit_datetime - prev > INTERVAL '30 minutes'
                           THEN 1 ELSE 0 END) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                       ) AS session_n
                  FROM ordered
            ), multi AS (
                SELECT visitor_id, session_n
                  FROM marked
              GROUP BY visitor_id, session_n
                HAVING COUNT(*) > 1
            )
            SELECT landing.label,
                   COUNT(*) AS visits
              FROM (
                    SELECT (ARRAY_AGG(m.label ORDER BY m.visit_datetime, m.id))[1] AS label
                      FROM marked m
                      JOIN multi u
                        ON u.visitor_id = m.visitor_id
                       AND u.session_n = m.session_n
                  GROUP BY m.visitor_id, m.session_n
              ) landing
          GROUP BY landing.label
          ORDER BY visits DESC, landing.label
             LIMIT 8
        """, (website.id, start_dt, site_host))
        landings = cr.dictfetchall()

        cr.execute("""
            WITH base AS (
                SELECT t.visitor_id,
                       t.id,
                       t.visit_datetime,
                       COALESCE(NULLIF(page.url, ''), NULLIF(path.path, ''), '/') AS label
                  FROM website_track t
                  JOIN website_visitor v ON v.id = t.visitor_id
                  LEFT JOIN website_page page ON page.id = t.page_id
                  CROSS JOIN LATERAL (
                        SELECT regexp_replace(split_part(t.url, '?', 1), '^https?://[^/]+', '') AS path
                  ) path
                 WHERE v.website_id = %s
                   AND t.visit_datetime >= %s
                   AND t.url IS NOT NULL
                   AND """ + public_visitor + """
                   AND """ + on_site + """
            ), ordered AS (
                SELECT base.*,
                       LAG(visit_datetime) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                       ) AS prev
                  FROM base
            ), marked AS (
                SELECT ordered.*,
                       SUM(CASE
                           WHEN prev IS NULL OR visit_datetime - prev > INTERVAL '30 minutes'
                           THEN 1 ELSE 0 END) OVER (
                           PARTITION BY visitor_id ORDER BY visit_datetime, id
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                       ) AS session_n
                  FROM ordered
            ), multi AS (
                SELECT visitor_id, session_n
                  FROM marked
              GROUP BY visitor_id, session_n
                HAVING COUNT(*) > 1
            ), steps AS (
                SELECT m.label,
                       LAG(m.label) OVER (
                           PARTITION BY m.visitor_id, m.session_n
                           ORDER BY m.visit_datetime, m.id
                       ) AS previous_label
                  FROM marked m
                  JOIN multi u
                    ON u.visitor_id = m.visitor_id
                   AND u.session_n = m.session_n
            )
            SELECT previous_label || ' → ' || label AS label,
                   COUNT(*) AS visits
              FROM steps
             WHERE previous_label IS NOT NULL
               AND previous_label <> label
          GROUP BY previous_label, label
          ORDER BY visits DESC, label
             LIMIT 8
        """, (website.id, start_dt, site_host))
        flows = cr.dictfetchall()

        session_count = sessions['sessions'] or 0
        page_views = int(sessions['page_views'] or 0)
        single = sessions['single_page'] or 0
        visitors = cohort['new_visitors'] + cohort['returning_visitors']
        pages_per_session = round(page_views / session_count, 1) if session_count else 0
        multi_session_count = sessions['multi_sessions'] or 0
        multi_page_views = int(sessions['multi_page_views'] or 0)
        multi_pages_per_session = round(multi_page_views / multi_session_count, 1) if multi_session_count else 0
        prev_session_count = previous_sessions['sessions'] or 0
        prev_page_views = int(previous_sessions['page_views'] or 0)
        prev_pages_per_session = round(prev_page_views / prev_session_count, 1) if prev_session_count else 0
        return {
            'website_name': website.name,
            'days': days,
            'online': online,
            'visitors': visitors,
            'page_views': page_views,
            'sessions': session_count,
            'pages_per_session': pages_per_session,
            'avg_duration': self._format_visit_duration(sessions['avg_seconds']),
            'single_page_rate': round(100 * single / session_count) if session_count else 0,
            'new_visitors': cohort['new_visitors'],
            'returning_visitors': cohort['returning_visitors'],
            'series': {
                'labels': labels,
                'visitors': visitors_series,
                'page_views': views_series,
                'multi_visitors': multi_visitors,
                'multi_page_views': multi_views,
            },
            'pages': pages,
            'countries': countries,
            'hours': hours,
            'landings': landings,
            'flows': flows,
            'multi': {
                'visitors': int(sessions['multi_visitors'] or 0),
                'page_views': multi_page_views,
                'sessions': multi_session_count,
                'avg_duration': self._format_visit_duration(sessions['avg_seconds']),
                'pages_per_session': multi_pages_per_session,
            },
            'previous': {
                'visitors': previous_visitors,
                'visitors_delta': self._analytics_change(visitors, previous_visitors),
                'page_views': prev_page_views,
                'page_views_delta': self._analytics_change(page_views, prev_page_views),
                'sessions': prev_session_count,
                'sessions_delta': self._analytics_change(session_count, prev_session_count),
                'pages_per_session': prev_pages_per_session,
                'pages_per_session_delta': self._analytics_change(pages_per_session, prev_pages_per_session),
                'avg_duration': self._format_visit_duration(previous_sessions['avg_seconds']),
                'avg_duration_delta': self._analytics_change(sessions['avg_seconds'], previous_sessions['avg_seconds']),
            },
        }

    @api.model
    def _empty_multi(self):
        return {
            'visitors': 0,
            'page_views': 0,
            'sessions': 0,
            'avg_duration': '—',
            'pages_per_session': 0,
        }

    @api.model
    def _empty_previous_period(self):
        return {
            'visitors': 0,
            'visitors_delta': None,
            'page_views': 0,
            'page_views_delta': None,
            'sessions': 0,
            'sessions_delta': None,
            'pages_per_session': 0,
            'pages_per_session_delta': None,
            'avg_duration': '—',
            'avg_duration_delta': None,
        }

    @api.model
    def _analytics_change(self, current, previous):
        if current is None or not previous:
            return None
        return int(round(100.0 * (float(current) - float(previous)) / float(previous)))

    @api.model
    def _format_visit_duration(self, seconds):
        if not seconds:
            return '—'
        seconds = int(round(seconds))
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return '%d h %02d' % (hours, minutes)
        if minutes:
            return '%d min %02d s' % (minutes, sec)
        return '%d s' % sec
