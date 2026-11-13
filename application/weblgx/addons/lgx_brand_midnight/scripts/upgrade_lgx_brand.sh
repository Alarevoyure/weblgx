#!/usr/bin/env bash
# Met à jour (ou installe) le module lgx_brand_midnight et régénère les assets.
#
# Usage:
#   sudo ./upgrade_lgx_brand.sh
#   sudo DB_NAME=autre_base ./upgrade_lgx_brand.sh
#
# Équivalent à :
#   sudo -u weblgx /usr/bin/weblgx -c /etc/weblgx/weblgx.conf -d weblgx -u lgx_brand_midnight --stop-after-init

set -euo pipefail

WEBLGX_BIN="${WEBLGX_BIN:-/usr/bin/weblgx}"
WEBLGX_CONF="${WEBLGX_CONF:-/etc/weblgx/weblgx.conf}"
WEBLGX_USER="${WEBLGX_USER:-weblgx}"
DB_NAME="${DB_NAME:-weblgx}"
MODULE="${MODULE:-lgx_brand_midnight}"

EXTRA_ARGS=("-u" "${MODULE}" "--stop-after-init")
if [[ "${INSTALL_FIRST:-0}" == "1" ]]; then
  EXTRA_ARGS=("-i" "${MODULE}" "--stop-after-init")
fi

exec sudo -u "${WEBLGX_USER}" "${WEBLGX_BIN}" -c "${WEBLGX_CONF}" -d "${DB_NAME}" "${EXTRA_ARGS[@]}"
