# Rôle PostgreSQL et mot de passe. Sourcé par install_weblgx.

[[ -n "${WEBLGX_INSTALL_RUNNING:-}" ]] || die "Lancer install_weblgx."

log "Attente de PostgreSQL."
ready=0
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then
    ready=1
    break
  fi
  sleep 1
done
[[ "${ready}" -eq 1 ]] || die "PostgreSQL ne répond pas."

role_exists="$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${WEBLGX_DB_USER}'" || true)"
if [[ "${role_exists}" != "1" ]]; then
  log "Création du rôle ${WEBLGX_DB_USER}."
  sudo -u postgres psql -v ON_ERROR_STOP=1 \
    -c "CREATE ROLE ${WEBLGX_DB_USER} LOGIN CREATEDB PASSWORD '${DB_PASSWORD}'"
else
  log "Rôle ${WEBLGX_DB_USER} déjà présent. Mot de passe aligné sur le fichier de secrets."
  sudo -u postgres psql -v ON_ERROR_STOP=1 \
    -c "ALTER ROLE ${WEBLGX_DB_USER} WITH LOGIN CREATEDB PASSWORD '${DB_PASSWORD}'"
fi

hba="$(sudo -u postgres psql -tAc 'SHOW hba_file' | tr -d '[:space:]')"
[[ -n "${hba}" && -f "${hba}" ]] || die "Fichier pg_hba.conf introuvable."
if ! grep -Eq '^[[:space:]]*host[[:space:]]+all[[:space:]]+all[[:space:]]+127\.0\.0\.1/32[[:space:]]+scram-sha-256' "${hba}"; then
  printf '\nhost all all 127.0.0.1/32 scram-sha-256\n' >> "${hba}"
  systemctl reload postgresql
fi

if ! PGPASSWORD="${DB_PASSWORD}" psql -h 127.0.0.1 -U "${WEBLGX_DB_USER}" -d postgres -v ON_ERROR_STOP=1 -c 'SELECT 1' >/dev/null; then
  die "Connexion PostgreSQL refusée pour ${WEBLGX_DB_USER}."
fi
log "Connexion PostgreSQL par mot de passe vérifiée."
