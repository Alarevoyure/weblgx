# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slug
from odoo.osv import expression


def mail_group_selected_site_domain(records):
    """Limite les listes backend au site de la société active.

    Une liste sans ``website_id`` est partagée par tous les sites : elle est exclue.
    ``sudo()`` (envoi, cron) n'est pas restreint. Sur le site public, la société
    du contexte est déjà celle du site servi.
    """
    if records.env.su or records.env.context.get("mail_group_skip_website_isolation"):
        return []
    company = records.env.company
    if not company:
        return []
    if records._name == "mail.group.moderation":
        return [("mail_group_id.website_id.company_id", "=", company.id)]
    return [("website_id.company_id", "=", company.id)]


def mail_group_default_website_id(env):
    """Site de la société active, ou le site explicitement demandé."""
    Website = env["website"]
    for key in ("default_website_id", "website_id"):
        wid = env.context.get(key)
        if not wid:
            continue
        website = Website.browse(int(wid)).exists()
        if website and (env.su or not website.company_id or website.company_id == env.company):
            return website.id
    website = Website.search(
        [("company_id", "=", env.company.id)],
        limit=1,
        order="sequence, id",
    )
    return website.id or False


class MailGroup(models.Model):
    _name = "mail.group"
    _inherit = "mail.group"

    website_id = fields.Many2one(
        "website",
        string="Site web",
        ondelete="cascade",
        index=True,
        default=lambda self: mail_group_default_website_id(self.env),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="website_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = mail_group_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )

    @api.onchange("website_id")
    def _onchange_website_id_alias_domain(self):
        company = self.website_id.company_id
        if company and company.alias_domain_id:
            self.alias_domain_id = company.alias_domain_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("website_id"):
                website_id = mail_group_default_website_id(self.env)
                if website_id:
                    vals["website_id"] = website_id
        return super().create(vals_list)

    def action_go_to_website(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/groups/%s" % slug(self),
        }


class MailGroupModeration(models.Model):
    _inherit = "mail.group.moderation"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        extra = mail_group_selected_site_domain(self)
        if extra:
            domain = expression.AND([domain, extra])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            access_rights_uid=access_rights_uid,
        )
