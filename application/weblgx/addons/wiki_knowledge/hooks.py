from weblgx import SUPERUSER_ID, api

_OBSOLETE_WIKI_PUBLIC_RULE_XMLIDS = (
    "wiki_knowledge.wiki_page_rule_public_published_only",
    "wiki_knowledge.wiki_page_rule_public_keep_last_published",
)


_WEBSITE_QWEB_COMPANY_DOMAIN = (
    "['&', ('type', '=', 'qweb'), '|', ('website_id', '=', False), "
    "('website_id.company_id', 'in', user.company_ids.ids)]"
)


def patch_website_company_security_rules(env):
    """Applique le filtre société sur la règle qweb (noupdate dans website)."""
    rule = env.ref("website.website_designer_edit_qweb", raise_if_not_found=False)
    if rule and rule.domain_force != _WEBSITE_QWEB_COMPANY_DOMAIN:
        rule.sudo().write({"domain_force": _WEBSITE_QWEB_COMPANY_DOMAIN})


def unlink_obsolete_wiki_public_ir_rules(env):
    """Supprime les deux anciennes ir.rule publiques remplacées par wiki_page_rule_public_visible."""
    for xid in _OBSOLETE_WIKI_PUBLIC_RULE_XMLIDS:
        rule = env.ref(xid, raise_if_not_found=False)
        if rule and rule.exists():
            rule.unlink()


def deactivate_orphan_module_views(env):
    """Désactive les vues héritées de modules retirés de Web@LGX."""
    env.cr.execute("""
        SELECT v.id
          FROM ir_ui_view v
          JOIN ir_model_data md ON md.model = 'ir.ui.view' AND md.res_id = v.id
         WHERE v.active = true
           AND md.module IS NOT NULL
           AND md.module NOT IN (SELECT name FROM ir_module_module)
    """)
    view_ids = [row[0] for row in env.cr.fetchall()]
    if view_ids:
        env["ir.ui.view"].browse(view_ids).write({"active": False})


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    unlink_obsolete_wiki_public_ir_rules(env)
    patch_website_company_security_rules(env)
    deactivate_orphan_module_views(env)
    website_model = env["website"].sudo()
    wiki_model = env["wiki.page"].sudo()

    target_website = website_model.search([("company_id", "=", 1)], limit=1)
    if not target_website:
        target_website = website_model.search([], limit=1)
    if not target_website:
        return

    pages = wiki_model.search([])
    if pages:
        pages.write({"website_id": target_website.id})

    try:
        website_model._wiki_ensure_headers()
        website_model._wiki_ensure_footers()
        website_model._wiki_ensure_logos()
    except Exception:
        pass
