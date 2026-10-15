# Dépendances système, puis copie de l'application Web@LGX du kit.
# Sourcé par install_weblgx.

[[ -n "${WEBLGX_INSTALL_RUNNING:-}" ]] || die "Lancer install_weblgx."

cache="/var/cache/weblgx"
mkdir -p "${cache}"

if ! command -v wkhtmltopdf >/dev/null 2>&1; then
  log "Installation de wkhtmltopdf."
  wk_deb="${cache}/wkhtmltox.deb"
  fetch "${WKHTML_DEB_URL}" "${wk_deb}"
  apt-get install -y "${wk_deb}"
fi

# Debian 13 n'a plus python3-pypdf2. Le code accepte python3-pypdf.
ensure_pypdf() {
  if apt-cache show python3-pypdf2 >/dev/null 2>&1; then
    apt-get install -y python3-pypdf2
    return
  fi
  log "Paquet de transition python3-pypdf2 vers python3-pypdf."
  local work="${cache}/pypdf-bridge"
  rm -rf "${work}"
  mkdir -p "${work}/DEBIAN"
  cat > "${work}/DEBIAN/control" <<'EOF'
Package: python3-pypdf2
Version: 99.0.0
Section: python
Priority: optional
Architecture: all
Depends: python3-pypdf
Maintainer: Web@LGX <contact@loegaux.fr>
Description: transitional package for Web@LGX
 Empty package so python3-pypdf2 resolves to python3-pypdf.
EOF
  dpkg-deb -b "${work}" "${cache}/python3-pypdf2-bridge.deb" >/dev/null
  rm -rf "${work}"
  apt-get install -y "${cache}/python3-pypdf2-bridge.deb"
}

log "Installation des dépendances Python et des polices."
apt-get install -y \
  adduser \
  fonts-dejavu-core \
  fonts-font-awesome \
  fonts-inconsolata \
  fonts-roboto-unhinted \
  fonts-urw-base35 \
  gsfonts \
  libjs-underscore \
  lsb-base \
  python3-babel \
  python3-chardet \
  python3-cryptography \
  python3-dateutil \
  python3-decorator \
  python3-docutils \
  python3-freezegun \
  python3-geoip2 \
  python3-gevent \
  python3-greenlet \
  python3-idna \
  python3-jinja2 \
  python3-libsass \
  python3-markupsafe \
  python3-num2words \
  python3-ofxparse \
  python3-openssl \
  python3-passlib \
  python3-pil \
  python3-polib \
  python3-psutil \
  python3-psycopg2 \
  python3-pydot \
  python3-qrcode \
  python3-renderpm \
  python3-reportlab \
  python3-requests \
  python3-rjsmin \
  python3-serial \
  python3-stdnum \
  python3-tz \
  python3-urllib3 \
  python3-usb \
  python3-vobject \
  python3-werkzeug \
  python3-xlrd \
  python3-xlsxwriter \
  python3-xlwt \
  python3-zeep
if apt-cache show python3-lxml-html-clean >/dev/null 2>&1; then
  apt-get install -y python3-lxml-html-clean
elif apt-cache show python3-lxml >/dev/null 2>&1; then
  apt-get install -y python3-lxml
else
  die "Paquet python3-lxml introuvable."
fi
ensure_pypdf

app="${ROOT}/application/weblgx"
[[ -d "${app}/addons" && -f "${ROOT}/application/bin/weblgx" ]] \
  || die "L'application Web@LGX est absente du kit. Sur la machine de référence : ./refresh_application.sh"

log "Copie de l'application Web@LGX."
rm -rf /usr/lib/python3/dist-packages/weblgx
if [[ -L /usr/lib/python3/dist-packages/odoo || -e /usr/lib/python3/dist-packages/odoo ]]; then
  rm -rf /usr/lib/python3/dist-packages/odoo
fi
cp -a "${app}" /usr/lib/python3/dist-packages/weblgx
ln -s weblgx /usr/lib/python3/dist-packages/odoo
install -m 755 "${ROOT}/application/bin/weblgx" /usr/bin/weblgx

# shellcheck disable=SC1091
source "${ROOT}/lib/link-type1-fonts.sh"
log "Application Web@LGX installée."
