#!/usr/bin/env bash
# Recopie l'application Web@LGX de cette machine dans le kit.
# À lancer sur la machine de référence, après une modification de module.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC=/usr/lib/python3/dist-packages/weblgx
DEST="${ROOT}/application/weblgx"

[[ -d "${SRC}/addons" ]] || {
  echo "Application introuvable : ${SRC}" >&2
  exit 1
}
[[ -f /usr/bin/weblgx ]] || {
  echo "Commande introuvable : /usr/bin/weblgx" >&2
  exit 1
}

rm -rf "${DEST}"
mkdir -p "${DEST}/addons" "${ROOT}/application/bin"

find "${SRC}" -mindepth 1 -maxdepth 1 ! -name addons -print0 \
  | xargs -0 cp -a -t "${DEST}/"
cp -a "${SRC}/addons/__init__.py" "${DEST}/addons/__init__.py"

while IFS= read -r name || [[ -n "${name}" ]]; do
  [[ -z "${name}" || "${name}" == \#* ]] && continue
  [[ -d "${SRC}/addons/${name}" ]] || {
    echo "Module absent de l'application : ${name}" >&2
    exit 1
  }
  cp -a "${SRC}/addons/${name}" "${DEST}/addons/${name}"
done < "${ROOT}/etc/modules.list"

find "${DEST}" -type d -name '__pycache__' -print0 | xargs -0 -r rm -rf
find "${DEST}" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.broken' \) -delete

cp -a /usr/bin/weblgx "${ROOT}/application/bin/weblgx"
chmod 755 "${ROOT}/application/bin/weblgx"

echo "Application copiée dans ${ROOT}/application ($(du -sh "${ROOT}/application" | awk '{print $1}'))."
