# weblgx.conf, création de la base et compte administrateur.
# Sourcé par install_weblgx.

[[ -n "${WEBLGX_INSTALL_RUNNING:-}" ]] || die "Lancer install_weblgx."

addons_path="${WEBLGX_ENGINE_ADDONS}"
install -d -m 750 -o root -g "${WEBLGX_SYSTEM_USER}" /etc/weblgx
sed \
  -e "s|__MASTER_PASSWORD__|${MASTER_PASSWORD}|g" \
  -e "s|__DB_USER__|${WEBLGX_DB_USER}|g" \
  -e "s|__DB_PASSWORD__|${DB_PASSWORD}|g" \
  -e "s|__DB_NAME__|${WEBLGX_DB_NAME}|g" \
  -e "s|__ADDONS_PATH__|${addons_path}|g" \
  -e "s|__DATA_DIR__|${WEBLGX_DATA_DIR}|g" \
  -e "s|__LOG_FILE__|${WEBLGX_LOG_FILE}|g" \
  -e "s|__HTTP_PORT__|${WEBLGX_HTTP_PORT}|g" \
  "${ROOT}/etc/weblgx.conf.template" > "${WEBLGX_CONFIG}"
chown root:"${WEBLGX_SYSTEM_USER}" "${WEBLGX_CONFIG}"
chmod 640 "${WEBLGX_CONFIG}"
log "Configuration écrite dans ${WEBLGX_CONFIG}."

db_exists="$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${WEBLGX_DB_NAME}'" || true)"
website_state="$(sudo -u postgres psql -d "${WEBLGX_DB_NAME}" -tAc "SELECT state FROM ir_module_module WHERE name='website'" 2>/dev/null || true)"
website_state="${website_state//[[:space:]]/}"
if [[ "${db_exists}" == "1" && "${website_state}" == "installed" ]]; then
  modules_csv="$(IFS=,; echo "${WEBLGX_MODULES[*]}")"
  log "La base ${WEBLGX_DB_NAME} existe déjà. Installation des modules manquants et mise à jour des autres."
  sudo -u "${WEBLGX_SYSTEM_USER}" /usr/bin/weblgx \
    --config "${WEBLGX_CONFIG}" \
    --logfile=False \
    -d "${WEBLGX_DB_NAME}" \
    -i "${modules_csv}" \
    -u "${modules_csv}" \
    --stop-after-init \
    --no-http 2>&1 | tee -a "${WEBLGX_LOG_FILE}"
  log "Modules à jour."
else
  if [[ "${db_exists}" == "1" ]]; then
    log "La base ${WEBLGX_DB_NAME} est incomplète. Elle est supprimée puis recréée."
    systemctl stop weblgx.service >/dev/null 2>&1 || true
    sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -c \
      "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${WEBLGX_DB_NAME}' AND pid <> pg_backend_pid();" \
      >/dev/null
    sudo -u postgres dropdb --if-exists "${WEBLGX_DB_NAME}"
  fi
  modules_csv="$(IFS=,; echo "${WEBLGX_MODULES[*]}")"
  log "Création de la base ${WEBLGX_DB_NAME} et installation des modules. Cette étape dure plusieurs minutes."
  log "La progression et les erreurs s'affichent ci-dessous."
  sudo -u "${WEBLGX_SYSTEM_USER}" /usr/bin/weblgx \
    --config "${WEBLGX_CONFIG}" \
    --logfile=False \
    -d "${WEBLGX_DB_NAME}" \
    -i "${modules_csv}" \
    --load-language="${WEBLGX_LANG}" \
    --without-demo=all \
    --skip-auto-install \
    --stop-after-init \
    --no-http 2>&1 | tee -a "${WEBLGX_LOG_FILE}"

  password_file="$(mktemp /run/weblgx-admin.XXXXXX)"
  chmod 600 "${password_file}"
  printf '%s' "${ADMIN_PASSWORD}" > "${password_file}"
  chown "${WEBLGX_SYSTEM_USER}:${WEBLGX_SYSTEM_USER}" "${password_file}"

  log "Définition du mot de passe administrateur."
  sudo -u "${WEBLGX_SYSTEM_USER}" env WEBLGX_ADMIN_PASSWORD_FILE="${password_file}" WEBLGX_LANG="${WEBLGX_LANG}" \
    timeout 180 /usr/bin/weblgx shell \
    --config "${WEBLGX_CONFIG}" \
    --logfile=False \
    -d "${WEBLGX_DB_NAME}" \
    --no-http <<'PY'
import os
from pathlib import Path

password = Path(os.environ["WEBLGX_ADMIN_PASSWORD_FILE"]).read_text()
lang_code = os.environ.get("WEBLGX_LANG") or "fr_FR"
admin = env.ref("base.user_admin")
admin.password = password
lang = env["res.lang"].search([("code", "=", lang_code)], limit=1)
if lang:
    if not lang.active:
        lang.active = True
    admin.lang = lang_code
    admin.partner_id.lang = lang_code
env.cr.commit()
PY
  rm -f "${password_file}"
  log "Base ${WEBLGX_DB_NAME} prête."
fi

owned="$(sudo -u postgres psql -tAc "SELECT COUNT(*) FROM pg_database WHERE datdba = (SELECT oid FROM pg_roles WHERE rolname='odoo')" || true)"
if [[ "${owned}" == "0" ]]; then
  sudo -u postgres dropuser --if-exists odoo >/dev/null 2>&1 || true
fi
