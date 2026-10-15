# Fonctions partagées. Ce fichier est sourcé par install_weblgx.

log() {
  printf '[weblgx] %s\n' "$*"
}

print_access() {
  local address
  address="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [[ -n "${address}" ]] || address="127.0.0.1"
  cat <<EOF

Connexion Web@LGX
  Adresse      : http://${address}:${WEBLGX_HTTP_PORT:-8069}
  Compte       : admin
  Mot de passe : ${ADMIN_PASSWORD:-voir le fichier ci-dessous}
  Secrets      : ${WEBLGX_CREDENTIALS:-/root/weblgx-credentials.txt}
EOF
}

report_failure() {
  trap - ERR
  printf '\n[weblgx] L'\''installation n'\''est pas terminée. Le service ne répond pas encore.\n' >&2
  printf '[weblgx] La cause est dans les messages affichés au-dessus.\n' >&2
  printf '[weblgx] Relancer : sudo ./install_weblgx\n' >&2
  if [[ -f "${WEBLGX_LOG_FILE:-/var/log/weblgx/weblgx.log}" ]]; then
    printf '[weblgx] Dernières lignes de %s :\n' "${WEBLGX_LOG_FILE:-/var/log/weblgx/weblgx.log}" >&2
    tail -n 40 "${WEBLGX_LOG_FILE:-/var/log/weblgx/weblgx.log}" >&2 || true
  fi
  print_access >&2 || true
}

die() {
  printf '[weblgx] ERREUR: %s\n' "$*" >&2
  report_failure
  exit 1
}

require_root() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]] || die "Lancer install_weblgx avec les droits root."
}

require_debian() {
  [[ -r /etc/os-release ]] || die "Système non reconnu."
  # shellcheck disable=SC1091
  source /etc/os-release
  [[ "${ID:-}" == "debian" ]] || die "Debian requis. Système détecté : ${PRETTY_NAME:-inconnu}."
  case "${VERSION_ID:-}" in
    12|13) ;;
    *) die "Debian 12 ou 13 requis. Système détecté : ${PRETTY_NAME:-inconnu}." ;;
  esac
  [[ "$(dpkg --print-architecture)" == "amd64" ]] \
    || die "Architecture amd64 requise."
  log "Système reconnu : ${PRETTY_NAME}."
}

gen_secret() {
  openssl rand -hex 24
}

require_names() {
  local name
  for name in "${WEBLGX_DB_NAME}" "${WEBLGX_DB_USER}" "${WEBLGX_SYSTEM_USER}"; do
    [[ "${name}" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] || die "Nom invalide : ${name}"
  done
  [[ "${WEBLGX_HTTP_PORT}" =~ ^[0-9]+$ ]] || die "Port invalide : ${WEBLGX_HTTP_PORT}"
}

read_secret() {
  local key="$1" file="$2" line
  line="$(grep -E "^${key}=" "$file" | head -n 1 || true)"
  [[ -n "$line" ]] || die "Clé absente de ${file} : ${key}"
  printf '%s' "${line#*=}"
}

load_or_create_secrets() {
  if [[ -f "${WEBLGX_CREDENTIALS}" ]]; then
    DB_PASSWORD="$(read_secret db_password "${WEBLGX_CREDENTIALS}")"
    ADMIN_PASSWORD="$(read_secret admin_password "${WEBLGX_CREDENTIALS}")"
    MASTER_PASSWORD="$(read_secret master_password "${WEBLGX_CREDENTIALS}")"
    log "Secrets existants conservés (${WEBLGX_CREDENTIALS})."
    return
  fi

  DB_PASSWORD="$(gen_secret)"
  ADMIN_PASSWORD="$(gen_secret)"
  MASTER_PASSWORD="$(gen_secret)"
  umask 077
  mkdir -p "$(dirname "${WEBLGX_CREDENTIALS}")"
  cat > "${WEBLGX_CREDENTIALS}" <<EOF
db_user=${WEBLGX_DB_USER}
db_password=${DB_PASSWORD}
db_name=${WEBLGX_DB_NAME}
admin_login=admin
admin_password=${ADMIN_PASSWORD}
master_password=${MASTER_PASSWORD}
config=${WEBLGX_CONFIG}
EOF
  chmod 600 "${WEBLGX_CREDENTIALS}"
  log "Secrets générés dans ${WEBLGX_CREDENTIALS}."
}

fetch() {
  local url="$1" dest="$2"
  curl -fL --retry 5 --retry-delay 2 -o "${dest}" "${url}"
}
