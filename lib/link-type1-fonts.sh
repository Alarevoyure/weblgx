# Relie les anciens noms de polices attendus par reportlab
# vers les fichiers URW fournis par Debian 12 et 13.
# Sourcé par install_weblgx.

[[ -n "${WEBLGX_INSTALL_RUNNING:-}" ]] || die "Lancer install_weblgx."

log "Polices Type1 pour les PDF."
apt-get install -y fonts-urw-base35

dest="${TYPE1_DEST:-/usr/share/fonts/type1/gsfonts}"
mkdir -p "${dest}"

link_type1() {
  local legacy="$1" modern="$2" dir pfb afm
  pfb=""
  for dir in /usr/share/fonts/X11/Type1 /usr/share/fonts/type1/urw-base35; do
    if [[ -f "${dir}/${modern}.pfb" ]]; then
      pfb="${dir}/${modern}.pfb"
      break
    fi
  done
  [[ -n "${pfb}" ]] || die "Police introuvable : ${modern}.pfb"
  if [[ ! -e "${dest}/${legacy}.pfb" ]]; then
    ln -s "${pfb}" "${dest}/${legacy}.pfb"
  fi
  afm="/usr/share/fonts/type1/urw-base35/${modern}.afm"
  if [[ -f "${afm}" && ! -e "${dest}/${legacy}.afm" ]]; then
    ln -s "${afm}" "${dest}/${legacy}.afm"
  fi
}

link_type1 n019003l NimbusSans-Regular
link_type1 n019004l NimbusSans-Bold
link_type1 n019023l NimbusSans-Italic
link_type1 n019024l NimbusSans-BoldItalic
link_type1 n021003l NimbusRoman-Regular
link_type1 n021004l NimbusRoman-Bold
link_type1 n021023l NimbusRoman-Italic
link_type1 n021024l NimbusRoman-BoldItalic
link_type1 n022003l NimbusMonoPS-Regular
link_type1 n022004l NimbusMonoPS-Bold
link_type1 n022023l NimbusMonoPS-Italic
link_type1 n022024l NimbusMonoPS-BoldItalic
link_type1 s050000l StandardSymbolsPS
link_type1 d050000l D050000L
