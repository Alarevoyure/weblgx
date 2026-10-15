#!/bin/sh
# Supprime du paquet moteur les modules qui ne sont pas dans la liste Web@LGX.
set -eu
list=/usr/lib/weblgx/modules.list
addons=/usr/lib/python3/dist-packages/odoo/addons
[ -s "${list}" ] || exit 0
[ -d "${addons}" ] || exit 0
for dir in "${addons}"/*/; do
  [ -d "${dir}" ] || continue
  name=$(basename "${dir}")
  if ! grep -qx "${name}" "${list}"; then
    rm -rf "${dir}"
  fi
done
exit 0