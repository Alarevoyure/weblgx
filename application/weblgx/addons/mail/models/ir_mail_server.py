# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

_FALLBACK_COMPANY_ID = 1


class IrMailServer(models.Model):
    _name = 'ir.mail_server'
    _inherit = ['ir.mail_server']

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        # required côté formulaire ; False en base le temps de la migration.
        default=lambda self: self.env['res.company'].browse(_FALLBACK_COMPANY_ID).exists()
        and _FALLBACK_COMPANY_ID
        or self.env.company.id,
        index=True,
        help="Société utilisatrice de ce serveur SMTP. "
             "Si une société n'a aucun serveur actif, "
             "les paramètres de la société ID=1 sont utilisés.",
    )

    mail_template_ids = fields.One2many(
        comodel_name='mail.template',
        inverse_name='mail_server_id',
        string='Mail template using this mail server',
        readonly=True)

    def _active_usages_compute(self):
        usages_super = super()._active_usages_compute()
        for record in self.filtered('mail_template_ids'):
            usages_super.setdefault(record.id, []).extend(
                map(lambda t: _('%s (Email Template)', t.display_name), record.mail_template_ids)
            )
        return usages_super

    @api.model
    def _get_default_bounce_address(self):
        """ Compute the default bounce address. Try to use mail-defined config
        parameter bounce alias if set. """
        if self.env.company.bounce_email:
            return self.env.company.bounce_email
        return super()._get_default_bounce_address()

    @api.model
    def _get_default_from_address(self):
        """ Default from: try to use default_from defined on company's alias
        domain. """
        if default_from := self.env.company.default_from_email:
            return default_from
        return super()._get_default_from_address()

    @api.model
    def _mail_servers_for_company(self, company=None):
        """Serveurs SMTP actifs de la société ; repli sur la société ID=1.

        Les enregistrements sans société (legacy) sont traités comme société 1.
        """
        company = company or self.env.company
        company_id = company.id if company else _FALLBACK_COMPANY_ID
        MailServer = self.sudo()

        def _search(company_ids, include_empty=False):
            domain = [('active', '=', True)]
            if include_empty:
                domain += [
                    '|',
                    ('company_id', 'in', company_ids),
                    ('company_id', '=', False),
                ]
            else:
                domain.append(('company_id', 'in', company_ids))
            return MailServer.search(domain, order='sequence, id')

        servers = _search([company_id])
        if servers:
            return servers

        if company_id != _FALLBACK_COMPANY_ID:
            servers = _search([_FALLBACK_COMPANY_ID], include_empty=True)
            if servers:
                return servers

        # Société 1 (ou absente) : inclure aussi les serveurs sans société.
        return _search([_FALLBACK_COMPANY_ID], include_empty=True)

    @api.model
    def _find_mail_server(self, email_from, mail_servers=None):
        """Restreint le pool SMTP à la société courante, puis repli ID=1."""
        if mail_servers is None:
            mail_servers = self._mail_servers_for_company()
        return super()._find_mail_server(email_from, mail_servers=mail_servers)

    def _get_test_email_from(self):
        self.ensure_one()
        if from_filter_parts := [part.strip() for part in (self.from_filter or '').split(",") if part.strip()]:
            # find first found complete email in filter parts
            if mail_from := next((email for email in from_filter_parts if "@" in email), None):
                return mail_from
            # the mail server is configured for a domain that matches the default email address
            alias_domains = self.env['mail.alias.domain'].sudo().search([])
            matching = next(
                (alias_domain for alias_domain in alias_domains
                 if self._match_from_filter(alias_domain.default_from_email, self.from_filter)
                ), False
            )
            if matching:
                return matching.default_from_email
            # fake default_from "odoo@domain"
            return f"odoo@{from_filter_parts[0]}"
        # no from_filter or from_filter is configured for a domain different that
        # the default_from of company's alias_domain -> fallback
        return super()._get_test_email_from()

    @api.model
    def _lgx_assign_default_company(self):
        """Assigne la société 1 aux serveurs SMTP sans société (migration)."""
        self.sudo().search([('company_id', '=', False)]).write(
            {'company_id': _FALLBACK_COMPANY_ID}
        )
