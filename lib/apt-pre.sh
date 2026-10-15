#!/bin/sh
# Laisse un odoo.conf vide le temps d'un apt, pour le chown du postinst du paquet moteur.
set -eu
if [ ! -e /etc/odoo/odoo.conf ]; then
  mkdir -p /etc/odoo
  touch /etc/odoo/odoo.conf
  chmod 640 /etc/odoo/odoo.conf
  touch /run/weblgx-remove-odoo-conf
fi
exit 0
