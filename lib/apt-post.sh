#!/bin/sh
# Retire le odoo.conf provisoire et empêche le service odoo de rester actif.
set -eu
if [ -f /run/weblgx-remove-odoo-conf ]; then
  rm -f /etc/odoo/odoo.conf
  rmdir /etc/odoo 2>/dev/null || true
  rm -f /run/weblgx-remove-odoo-conf
fi
if command -v systemctl >/dev/null 2>&1; then
  systemctl stop odoo.service >/dev/null 2>&1 || true
  systemctl disable odoo.service >/dev/null 2>&1 || true
  systemctl mask odoo.service >/dev/null 2>&1 || true
  systemctl reset-failed odoo.service >/dev/null 2>&1 || true
fi
if [ -x /usr/lib/weblgx/prune-addons.sh ]; then
  /usr/lib/weblgx/prune-addons.sh
fi
exit 0
