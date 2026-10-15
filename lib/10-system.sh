# Paquets de base. Sourcé par install_weblgx.

[[ -n "${WEBLGX_INSTALL_RUNNING:-}" ]] || die "Lancer install_weblgx."

log "Installation des paquets système."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  adduser \
  ca-certificates \
  curl \
  fontconfig \
  gnupg \
  libjpeg62-turbo \
  libxext6 \
  libxrender1 \
  openssl \
  postgresql \
  postgresql-client \
  python3-ldap \
  rsync \
  xfonts-75dpi \
  xfonts-base

systemctl enable postgresql
systemctl start postgresql
