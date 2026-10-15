# Service systemd weblgx. Sourcé par install_weblgx.

[[ -n "${WEBLGX_INSTALL_RUNNING:-}" ]] || die "Lancer install_weblgx."

sed \
  -e "s|__SYSTEM_USER__|${WEBLGX_SYSTEM_USER}|g" \
  -e "s|__CONFIG__|${WEBLGX_CONFIG}|g" \
  "${ROOT}/etc/weblgx.service" > /etc/systemd/system/weblgx.service
chmod 644 /etc/systemd/system/weblgx.service

sed \
  -e "s|__SYSTEM_USER__|${WEBLGX_SYSTEM_USER}|g" \
  "${ROOT}/etc/weblgx.logrotate" > /etc/logrotate.d/weblgx
chmod 644 /etc/logrotate.d/weblgx

systemctl stop weblgx.service >/dev/null 2>&1 || true
if ss -ltn 2>/dev/null | grep -q ":${WEBLGX_HTTP_PORT} "; then
  die "Le port ${WEBLGX_HTTP_PORT} est déjà utilisé."
fi

systemctl daemon-reload
systemctl enable weblgx.service
systemctl restart weblgx.service

ready=0
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null --max-time 5 "http://127.0.0.1:${WEBLGX_HTTP_PORT}/web/login"; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "${ready}" -ne 1 ]]; then
  journalctl -u weblgx.service -n 40 --no-pager >&2 || true
  die "La page de connexion ne répond pas sur le port ${WEBLGX_HTTP_PORT}."
fi
log "Service weblgx démarré, page de connexion disponible."
