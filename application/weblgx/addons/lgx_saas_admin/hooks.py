# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

CALENDAR_EVENT_EMPLOYEE_DOMAIN = (
    "['|', ('partner_ids', 'in', user.partner_id.id), "
    "('company_id', 'in', company_ids)]"
)
RES_USERS_RULE_DOMAIN = (
    "['|', ('id', '=', user.id), ('company_ids', 'in', user.company_ids.ids)]"
)
RES_PARTNER_COMPANY_DOMAIN = (
    "['|', ('partner_share', '!=', False), "
    "'|', ('company_id', 'in', user.company_ids.ids), ('company_id', '=', False)]"
)
COMPANY_DOMAIN = "[('id', 'in', user.company_ids.ids)]"
COMPANY_OR_SHARED_DOMAIN = (
    "['|', ('company_id', '=', False), ('company_id', 'in', user.company_ids.ids)]"
)
WEBSITE_OWNED_DOMAIN = (
    "['|', ('website_id', '=', False), "
    "('website_id.company_id', 'in', user.company_ids.ids)]"
)
VIEW_DOMAIN = (
    "['|', ('type', '!=', 'qweb'), '&', ('type', '=', 'qweb'), "
    "'|', ('website_id', '=', False), "
    "('website_id.company_id', 'in', user.company_ids.ids)]"
)

# Admin (group_system) keeps these rules, but they must not open every company.
# SuperAdmin has a separate (1=1) rule. noupdate records are forced here.
SCOPED_RULE_DOMAINS = {
    "base.res_company_rule_erp_manager": COMPANY_DOMAIN,
    "base.res_users_rule": RES_USERS_RULE_DOMAIN,
    "base.res_partner_rule": RES_PARTNER_COMPANY_DOMAIN,
    "calendar.calendar_event_rule_employee": CALENDAR_EVENT_EMPLOYEE_DOMAIN,
    "website.website_rule_company_users": COMPANY_OR_SHARED_DOMAIN,
    "website.website_rule_company_system": COMPANY_OR_SHARED_DOMAIN,
    "website.website_page_rule_company_editors": WEBSITE_OWNED_DOMAIN,
    "website.website_page_rule_company_system": WEBSITE_OWNED_DOMAIN,
    "website.website_menu_rule_company_editors": WEBSITE_OWNED_DOMAIN,
    "website.website_menu_rule_company_system": WEBSITE_OWNED_DOMAIN,
    "website.website_group_system_edit_all_views": VIEW_DOMAIN,
    "wiki_knowledge.wiki_page_rule_company_system": COMPANY_OR_SHARED_DOMAIN,
    "wiki_knowledge.wiki_gallery_rule_system": COMPANY_OR_SHARED_DOMAIN,
    "wiki_knowledge.wiki_gallery_lib_rule_system": COMPANY_OR_SHARED_DOMAIN,
    "wiki_knowledge.wiki_gallery_verified_email_rule_system": COMPANY_OR_SHARED_DOMAIN,
    "lgx_website_astuce.website_astuce_rule_system": COMPANY_OR_SHARED_DOMAIN,
    "lgx_livechat_website.im_livechat_channel_rule_system": WEBSITE_OWNED_DOMAIN,
    "lgx_website_attachment_isolation.ir_attachment_rule_website_system": WEBSITE_OWNED_DOMAIN,
}

# Full access that is not company data stays on Admin. Cross-company chat does not.
SUPERADMIN_ONLY_RULES = (
    "mail.ir_rule_discuss_channel_group_system",
    "mail.ir_rule_discuss_channel_member_group_system",
)

DEMOTE_PARAM = "lgx_saas_admin.demote_extra_superadmins"


def _force_rule_domain(env, xmlid, domain):
    rule = env.ref(xmlid, raise_if_not_found=False)
    if rule and (rule.domain_force or "").strip() != domain:
        rule.sudo().write({"domain_force": domain})
        _logger.info("lgx_saas_admin: scoped rule %s", xmlid)


def _force_rule_groups(env, xmlid, group):
    rule = env.ref(xmlid, raise_if_not_found=False)
    if rule and group and set(rule.groups.ids) != set(group.ids):
        rule.sudo().write({"groups": [(6, 0, group.ids)]})
        _logger.info("lgx_saas_admin: superadmin-only rule %s", xmlid)


def _rename_admin_group(env):
    """Settings is the company Admin. SuperAdmin stays above it."""
    group = env.ref("base.group_system", raise_if_not_found=False)
    if not group:
        return
    labels = {
        "en_US": (
            "Admin",
            "Same administration rights as SuperAdmin, limited to the user's allowed companies.",
        ),
        "fr_FR": (
            "Admin",
            "Mêmes droits d'administration que SuperAdmin, limités aux sociétés autorisées de l'utilisateur.",
        ),
    }
    for lang, (name, comment) in labels.items():
        group.with_context(lang=lang).write({"name": name, "comment": comment})


def _demote_extra_superadmins(env):
    """One shot: SuperAdmin except Administrator / WeblgxBot becomes Admin.

    Those accounts keep Settings (Admin) and their allowed companies.
    A later manual promotion to SuperAdmin is left untouched.
    """
    icp = env["ir.config_parameter"].sudo()
    if icp.get_param(DEMOTE_PARAM):
        return
    group_super = env.ref("lgx_saas_admin.group_superadmin", raise_if_not_found=False)
    if not group_super:
        icp.set_param(DEMOTE_PARAM, "1")
        return
    keep = env["res.users"]
    for xmlid in ("base.user_admin", "base.user_root"):
        user = env.ref(xmlid, raise_if_not_found=False)
        if user:
            keep |= user
    extras = group_super.with_context(active_test=False).users - keep
    if extras:
        extras.with_context(lgx_skip_superadmin_company_sync=True).sudo().write({
            "groups_id": [(3, group_super.id)],
        })
        for user in extras:
            _logger.info(
                "lgx_saas_admin: %s (%s) moved from SuperAdmin to Admin",
                user.login,
                user.id,
            )
    icp.set_param(DEMOTE_PARAM, "1")


def apply_saas_record_rules(env):
    """Company-scoped Admin, global SuperAdmin, and SaaS record rules."""
    for xmlid, domain in SCOPED_RULE_DOMAINS.items():
        _force_rule_domain(env, xmlid, domain)

    group_super = env.ref("lgx_saas_admin.group_superadmin", raise_if_not_found=False)
    for xmlid in SUPERADMIN_ONLY_RULES:
        _force_rule_groups(env, xmlid, group_super)

    _rename_admin_group(env)
    _demote_extra_superadmins(env)
    env["res.users"].sudo()._lgx_sync_superadmin_companies()
    _ensure_erp_implies_partner_manager(env)


def post_init_hook(env):
    """Install path: same role split as a module upgrade."""
    group_super = env.ref("lgx_saas_admin.group_superadmin", raise_if_not_found=False)
    user_admin = env.ref("base.user_admin", raise_if_not_found=False)
    user_root = env.ref("base.user_root", raise_if_not_found=False)
    if group_super:
        privileged = env["res.users"]
        if user_admin:
            privileged |= user_admin
        if user_root:
            privileged |= user_root
        missing = privileged.filtered(lambda user: group_super not in user.groups_id)
        if missing:
            missing.sudo().write({"groups_id": [(4, group_super.id)]})
    apply_saas_record_rules(env)


def _ensure_erp_implies_partner_manager(env):
    """Access Rights implies Contact Creation (users + company details)."""
    group_erp = env.ref("base.group_erp_manager", raise_if_not_found=False)
    group_partner = env.ref("base.group_partner_manager", raise_if_not_found=False)
    if not group_erp or not group_partner:
        return
    if group_partner not in group_erp.implied_ids:
        group_erp.write({"implied_ids": [(4, group_partner.id)]})
        _logger.info("lgx_saas_admin: linked Contact Creation to Access Rights")
