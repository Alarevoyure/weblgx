# Utilisateur système et répertoires de données.
# Les modules sont déjà dans l'application copiée par 30-engine.sh.
# Sourcé par install_weblgx.

[[ -n "${WEBLGX_INSTALL_RUNNING:-}" ]] || die "Lancer install_weblgx."

for name in "${WEBLGX_MODULES[@]}"; do
  [[ -f "${WEBLGX_ENGINE_ADDONS}/${name}/__manifest__.py" ]] \
    || die "Module absent de l'application : ${name}"
done

if ! id "${WEBLGX_SYSTEM_USER}" >/dev/null 2>&1; then
  log "Création de l'utilisateur système ${WEBLGX_SYSTEM_USER}."
  adduser --system --group --home "${WEBLGX_DATA_DIR}" --shell /usr/sbin/nologin "${WEBLGX_SYSTEM_USER}"
fi

install -d -m 750 -o "${WEBLGX_SYSTEM_USER}" -g "${WEBLGX_SYSTEM_USER}" \
  "${WEBLGX_DATA_DIR}" "${WEBLGX_LOG_DIR}"
touch "${WEBLGX_LOG_FILE}"
chown "${WEBLGX_SYSTEM_USER}:${WEBLGX_SYSTEM_USER}" "${WEBLGX_LOG_FILE}"
log "Modules de l'application vérifiés (${#WEBLGX_MODULES[@]})."
