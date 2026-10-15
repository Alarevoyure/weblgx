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


def apply_saas_record_rules(env):
    """Force SaaS isolation rules (calendar + internal contacts)."""
    calendar_rule = env.ref(
        "calendar.calendar_event_rule_employee", raise_if_not_found=False
    )
    if calendar_rule and calendar_rule.domain_force != CALENDAR_EVENT_EMPLOYEE_DOMAIN:
        calendar_rule.sudo().write({"domain_force": CALENDAR_EVENT_EMPLOYEE_DOMAIN})
        _logger.info("lgx_saas_admin: applied calendar multi-company rule")

    partner_rule = env.ref("base.res_partner_rule", raise_if_not_found=False)
    if partner_rule and partner_rule.domain_force != RES_PARTNER_COMPANY_DOMAIN:
        partner_rule.sudo().write({"domain_force": RES_PARTNER_COMPANY_DOMAIN})
        _logger.info("lgx_saas_admin: applied res.partner multi-company rule")

    users_rule = env.ref("base.res_users_rule", raise_if_not_found=False)
    if users_rule and users_rule.domain_force != RES_USERS_RULE_DOMAIN:
        users_rule.sudo().write({"domain_force": RES_USERS_RULE_DOMAIN})
        _logger.info("lgx_saas_admin: applied res.users multi-company rule")


def post_init_hook(env):
    """Assign SuperAdmin to Administrator; demote other Settings users."""

    group_super = env.ref("lgx_saas_admin.group_superadmin", raise_if_not_found=False)
    group_system = env.ref("base.group_system", raise_if_not_found=False)
    group_erp = env.ref("base.group_erp_manager", raise_if_not_found=False)
    user_admin = env.ref("base.user_admin", raise_if_not_found=False)
    user_root = env.ref("base.user_root", raise_if_not_found=False)

    if not group_super or not group_system or not group_erp:
        return

    apply_saas_record_rules(env)

    privileged = env["res.users"].browse()
    if user_admin:
        privileged |= user_admin
    if user_root:
        privileged |= user_root

    for user in privileged:
        if group_super not in user.groups_id:
            user.write({"groups_id": [(4, group_super.id)]})

    if user_admin:
        all_companies = env["res.company"].sudo().search([])
        missing = all_companies - user_admin.company_ids
        if missing:
            user_admin.write({
                "company_ids": [(4, cid) for cid in missing.ids],
            })

    others = env["res.users"].sudo().search([
        ("groups_id", "in", group_system.id),
        ("id", "not in", privileged.ids),
        ("share", "=", False),
    ])
    for user in others:
        commands = [(4, group_erp.id), (3, group_system.id)]
        if group_super in user.groups_id:
            commands.append((3, group_super.id))
        user.write({"groups_id": commands})
        _logger.info(
            "lgx_saas_admin: demoted user %s (%s) from Settings to Access Rights",
            user.login,
            user.id,
        )

    _ensure_erp_implies_partner_manager(env)


def _ensure_erp_implies_partner_manager(env):
    """Access Rights implies Contact Creation (users + company details)."""
    group_erp = env.ref("base.group_erp_manager", raise_if_not_found=False)
    group_partner = env.ref("base.group_partner_manager", raise_if_not_found=False)
    if not group_erp or not group_partner:
        return
    if group_partner not in group_erp.implied_ids:
        group_erp.write({"implied_ids": [(4, group_partner.id)]})
        _logger.info("lgx_saas_admin: linked Contact Creation to Access Rights")
