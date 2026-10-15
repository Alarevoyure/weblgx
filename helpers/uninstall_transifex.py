#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Désinstallation du module « transifex » puis commit explicite.
À lancer sous l’utilisateur système prévu pour Odoo (souvent odoo).

Usage:
    ./uninstall_transifex.py -d NOM_BASE [-c /chemin/weblgx.conf]

Exemple:
    sudo -u weblgx ./uninstall_transifex.py -d weblgx -c /etc/weblgx/weblgx.conf
"""
from __future__ import annotations

import argparse
import sys

import odoo
from odoo import SUPERUSER_ID, api


def main() -> int:
    parser = argparse.ArgumentParser(description="Désinstaller le module transifex")
    parser.add_argument(
        "-d",
        "--database",
        required=True,
        help="Nom de la base PostgreSQL Odoo",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Fichier de configuration Odoo (recommandé en production)",
    )
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
        mods = env["ir.module.module"].search([("name", "=", "transifex")])
        if not mods:
            print(
                "Aucune ligne « transifex » dans ir.module.module.",
                file=sys.stderr,
            )
            return 1
        m = mods[0]
        if m.state != "installed":
            print(f"État « {m.state} » : pas de désinstallation nécessaire.")
            cr.rollback()
            return 0
        mods.button_immediate_uninstall()
        cr.commit()
        print("Module « transifex » désinstallé et transaction enregistrée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
