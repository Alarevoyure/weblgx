#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Désinstallation du module « transifex » puis commit explicite.
À lancer sous l’utilisateur système prévu pour Web@LGX (souvent weblgx).

Usage:
    ./uninstall_transifex.py -d NOM_BASE [-c /chemin/weblgx.conf]

Exemple:
    sudo -u weblgx ./uninstall_transifex.py -d weblgx -c /etc/weblgx/weblgx.conf
"""
from __future__ import annotations

import argparse
import sys

import weblgx
from weblgx import SUPERUSER_ID, api


def main() -> int:
    parser = argparse.ArgumentParser(description="Désinstaller le module transifex")
    parser.add_argument(
        "-d",
        "--database",
        required=True,
        help="Nom de la base PostgreSQL Web@LGX",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Fichier de configuration Web@LGX (recommandé en production)",
    )
    argv = parser.parse_args()

    cli: list[str] = []
    if argv.config:
        cli.extend(["-c", argv.config])
    cli.extend(["-d", argv.database])

    weblgx.tools.config.parse_config(cli)
    weblgx.cli.server.report_configuration()
    weblgx.modules.module.initialize_sys_path()
    weblgx.service.server.start(preload=[], stop=True)

    dbname = weblgx.tools.config["db_name"]
    registry = weblgx.registry(dbname)
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
