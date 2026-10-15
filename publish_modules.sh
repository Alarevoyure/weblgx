#!/usr/bin/env bash
# Recopie les modules de l'application dans le dépôt, puis les envoie sur GitHub.
# Le message du commit est la date et l'heure.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC=/usr/lib/python3/dist-packages/weblgx/addons
DEST="${ROOT}/application/weblgx/addons"
LIST="${ROOT}/etc/modules.list"

[[ -d "${SRC}" ]] || { echo "Application introuvable : ${SRC}" >&2; exit 1; }
[[ -f "${LIST}" ]] || { echo "Liste introuvable : ${LIST}" >&2; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "La commande gh est absente." >&2; exit 1; }

copied=()
while IFS= read -r name || [[ -n "${name}" ]]; do
  [[ -z "${name}" || "${name}" == \#* ]] && continue
  [[ -d "${SRC}/${name}" ]] || { echo "Module absent de l'application : ${name}" >&2; exit 1; }
  rm -rf "${DEST}/${name}"
  cp -a "${SRC}/${name}" "${DEST}/${name}"
  find "${DEST}/${name}" -type d -name '__pycache__' -print0 | xargs -0 -r rm -rf
  find "${DEST}/${name}" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.broken' \) -delete
  copied+=("application/weblgx/addons/${name}")
done < "${LIST}"

cd "${ROOT}"
git add -- "${copied[@]}"

if git diff --cached --quiet; then
  echo "Aucun changement à envoyer."
  exit 0
fi

login="$(gh api user --jq .login)"
uid="$(gh api user --jq .id)"
author="$(gh api user --jq '.name // empty')"
[[ -n "${author}" ]] || author="${login}"
email="${uid}+${login}@users.noreply.github.com"
message="$(date '+%Y-%m-%d %H:%M:%S')"

GIT_AUTHOR_NAME="${author}" \
GIT_AUTHOR_EMAIL="${email}" \
GIT_COMMITTER_NAME="${author}" \
GIT_COMMITTER_EMAIL="${email}" \
git commit -m "${message}"

git push
echo "Envoyé : ${message}"
