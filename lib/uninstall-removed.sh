# Désinstalle dans la base les modules absents du dépôt.
# À lancer avant de remplacer les fichiers : la désinstallation a besoin de l'ancien code.

uninstall_removed_modules() {
  [[ -x /usr/bin/weblgx && -f "${WEBLGX_CONFIG}" ]] || return 0
  local db_exists
  db_exists="$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${WEBLGX_DB_NAME}'" || true)"
  [[ "${db_exists}" == "1" ]] || return 0

  declare -A keep=()
  local name installed
  for name in "${WEBLGX_MODULES[@]}"; do
    keep["${name}"]=1
  done

  installed="$(sudo -u postgres psql -d "${WEBLGX_DB_NAME}" -tAc \
    "SELECT name FROM ir_module_module WHERE state IN ('installed', 'to upgrade')" 2>/dev/null || true)"

  local removed=()
  while IFS= read -r name; do
    name="${name//[[:space:]]/}"
    [[ -n "${name}" && "${name}" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] || continue
    [[ -n "${keep[${name}]:-}" ]] || removed+=("${name}")
  done <<< "${installed}"
  [[ ${#removed[@]} -gt 0 ]] || return 0

  local sql_removed="" blocker blockers=()
  for name in "${removed[@]}"; do
    sql_removed+="'${name}',"
  done
  sql_removed="${sql_removed%,}"

  blocker="$(sudo -u postgres psql -d "${WEBLGX_DB_NAME}" -tAc "
    SELECT DISTINCT m.name
      FROM ir_module_module_dependency d
      JOIN ir_module_module m ON m.id = d.module_id
     WHERE d.name IN (${sql_removed})
       AND m.state IN ('installed', 'to upgrade')
       AND m.name NOT IN (${sql_removed})
  " || true)"
  while IFS= read -r name; do
    name="${name//[[:space:]]/}"
    [[ -n "${name}" && -n "${keep[${name}]:-}" ]] && blockers+=("${name}")
  done <<< "${blocker}"
  if [[ ${#blockers[@]} -gt 0 ]]; then
    die "Des modules conservés dépendent d'un module retiré : ${blockers[*]}. La base n'a pas été modifiée."
  fi

  local missing_code=()
  for name in "${removed[@]}"; do
    [[ -d "/usr/lib/python3/dist-packages/weblgx/addons/${name}" ]] || missing_code+=("${name}")
  done
  if [[ ${#missing_code[@]} -gt 0 ]]; then
    die "Le code de ${missing_code[*]} a déjà été remplacé. Restaurez ces dossiers, relancez l'installation, puis mettez le dépôt à jour."
  fi

  local csv
  csv="$(IFS=,; echo "${removed[*]}")"
  log "Désinstallation dans la base des modules retirés du dépôt : ${csv}"
  systemctl stop weblgx.service >/dev/null 2>&1 || true
  sudo -u "${WEBLGX_SYSTEM_USER}" env WEBLGX_REMOVE_MODULES="${csv}" \
    timeout 600 /usr/bin/weblgx shell \
    --config "${WEBLGX_CONFIG}" \
    --logfile=False \
    -d "${WEBLGX_DB_NAME}" \
    --no-http <<'PY'
import os
names = [n for n in os.environ.get("WEBLGX_REMOVE_MODULES", "").split(",") if n]
mods = env["ir.module.module"].search([
    ("name", "in", names),
    ("state", "in", ("installed", "to upgrade")),
])
if mods:
    mods.button_immediate_uninstall()
PY
  log "Modules retirés de la base."
}
