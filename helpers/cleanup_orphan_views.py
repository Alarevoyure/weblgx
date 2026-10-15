#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Désactive les vues dont le module XML d'origine n'existe plus dans ir_module_module.
Typique après retrait de modules Odoo (project, rating, sms…) dans Web@LGX.

Usage:
    ./cleanup_orphan_views.py -d NOM_BASE [-c /chemin/weblgx.conf]

Exemple:
    sudo -u weblgx ./cleanup_orphan_views.py -d weblgx -c /etc/weblgx/weblgx.conf
"""
from __future__ import annotations

import argparse
import sys

import odoo
from odoo import SUPERUSER_ID, api


def deactivate_orphan_module_views(env):
    env.cr.execute("""
        SELECT v.id, v.name, v.model, md.module
          FROM ir_ui_view v
          JOIN ir_model_data md ON md.model = 'ir.ui.view' AND md.res_id = v.id
         WHERE v.active = true
           AND md.module IS NOT NULL
           AND md.module NOT IN (SELECT name FROM ir_module_module)
         ORDER BY md.module, v.id
    """)
    rows = env.cr.fetchall()
    if not rows:
        return []

    view_ids = [row[0] for row in rows]
    env['ir.ui.view'].browse(view_ids).write({'active': False})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Désactiver les vues orphelines (modules absents)",
    )
    parser.add_argument("-d", "--database", required=True, help="Nom de la base PostgreSQL Odoo")
    parser.add_argument("-c", "--config", help="Fichier de configuration Odoo")
    argv = parser.parse_args()

    cli: list[str] = []
    if argv.config:
        cli.extend(["-c", argv.config])
    cli.extend(["-d", argv.database])

    odoo.tools.config.parse_config(cli)
    odoo.cli.server.report_configuration()
    odoo.modules.module.initialize_sys_path()
    odoo.service.server.start(preload=[], stop=True)

    dbname = odoo.tools.config["db_name"]
    registry = odoo.registry(dbname)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        rows = deactivate_orphan_module_views(env)
        cr.commit()
        if not rows:
            print("Aucune vue orpheline active trouvée.")
            return 0
        print(f"{len(rows)} vue(s) orpheline(s) désactivée(s) :")
        for view_id, name, model, module in rows:
            print(f"  - [{module}] {model} / {name} (id={view_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
