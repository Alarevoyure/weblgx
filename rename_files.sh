#!/usr/bin/env bash
# Renommage des fichiers/dossiers odoo* -> weblgx* dans application/weblgx
set -euo pipefail
cd "$(dirname "$0")/application/weblgx"

# --- Répertoires ---
git mv addons/mail/static/lib/odoo_sfu addons/mail/static/lib/weblgx_sfu
git mv addons/web/static/lib/odoo_ui_icons addons/web/static/lib/weblgx_ui_icons
git mv addons/web_editor/static/src/js/editor/odoo-editor addons/web_editor/static/src/js/editor/weblgx-editor
git mv addons/web_editor/static/src/scss/odoo-editor addons/web_editor/static/src/scss/weblgx-editor
git mv addons/website/static/src/libs/zoomodoo addons/website/static/src/libs/zoomweblgx
git mv addons/website/static/src/snippets/s_mega_menu_odoo_menu addons/website/static/src/snippets/s_mega_menu_weblgx_menu

# --- Fichiers dans les répertoires renommés ---
git mv addons/mail/static/lib/weblgx_sfu/odoo_sfu.js addons/mail/static/lib/weblgx_sfu/weblgx_sfu.js
git mv addons/mail/static/lib/weblgx_sfu/odoo_sfu.licenses.txt addons/mail/static/lib/weblgx_sfu/weblgx_sfu.licenses.txt
git mv addons/web/static/lib/weblgx_ui_icons/fonts/odoo_ui_icons.woff addons/web/static/lib/weblgx_ui_icons/fonts/weblgx_ui_icons.woff
git mv addons/web/static/lib/weblgx_ui_icons/fonts/odoo_ui_icons.woff2 addons/web/static/lib/weblgx_ui_icons/fonts/weblgx_ui_icons.woff2
git mv addons/web_editor/static/src/js/editor/weblgx-editor/src/OdooEditor.js addons/web_editor/static/src/js/editor/weblgx-editor/src/WeblgxEditor.js
git mv addons/web_editor/static/src/js/editor/weblgx-editor/test/spec/odooFields.test.js addons/web_editor/static/src/js/editor/weblgx-editor/test/spec/weblgxFields.test.js
git mv addons/website/static/src/libs/zoomweblgx/zoomodoo.js addons/website/static/src/libs/zoomweblgx/zoomweblgx.js
git mv addons/website/static/src/libs/zoomweblgx/zoomodoo.scss addons/website/static/src/libs/zoomweblgx/zoomweblgx.scss

# --- Fichiers individuels ---
git mv addons/base/tests/odoo.jpg addons/base/tests/weblgx.jpg
git mv addons/mail_bot/static/src/scss/odoobot_style.scss addons/mail_bot/static/src/scss/weblgxbot_style.scss
git mv addons/mail/static/scripts/odoo-mailgate.py addons/mail/static/scripts/weblgx-mailgate.py
git mv addons/mail/static/src/img/odoobot.png addons/mail/static/src/img/weblgxbot.png
git mv addons/mail/static/src/img/odoobot_transparent.png addons/mail/static/src/img/weblgxbot_transparent.png
git mv addons/mail/static/src/img/odoo_o.png addons/mail/static/src/img/weblgx_o.png
git mv addons/web_editor/static/src/img/odoobot_transparent.png addons/web_editor/static/src/img/weblgxbot_transparent.png
git mv addons/web_editor/tests/test_odoo_editor.py addons/web_editor/tests/test_weblgx_editor.py
git mv addons/website/static/src/img/snippets_thumbs/s_mega_menu_odoo_menu.svg addons/website/static/src/img/snippets_thumbs/s_mega_menu_weblgx_menu.svg
git mv addons/website/static/src/js/editor/odoo_editor.js addons/website/static/src/js/editor/weblgx_editor.js
git mv addons/website/views/snippets/s_mega_menu_odoo_menu.xml addons/website/views/snippets/s_mega_menu_weblgx_menu.xml
git mv addons/web/static/img/odoo-icon-192x192.png addons/web/static/img/weblgx-icon-192x192.png
git mv addons/web/static/img/odoo-icon-512x512.png addons/web/static/img/weblgx-icon-512x512.png
git mv addons/web/static/img/odoo-icon-ios.png addons/web/static/img/weblgx-icon-ios.png
git mv addons/web/static/img/odoo-icon.svg addons/web/static/img/weblgx-icon.svg
git mv addons/web/static/img/odoo_logo_dark.svg addons/web/static/img/weblgx_logo_dark.svg
git mv addons/web/static/img/odoo_logo.svg addons/web/static/img/weblgx_logo.svg
git mv addons/web/static/img/odoo_logo_tiny.png addons/web/static/img/weblgx_logo_tiny.png
git mv addons/web/static/lib/ace/ace.odoo-custom.js addons/web/static/lib/ace/ace.weblgx-custom.js
git mv addons/web/static/lib/owl/odoo_module.js addons/web/static/lib/owl/weblgx_module.js
git mv addons/web/tests/odoo.png addons/web/tests/weblgx.png
git mv tests/_odoo_checker_markup.py tests/_weblgx_checker_markup.py

# --- Suppression des sauvegardes ---
git rm -q addons/web/static/img/odoo-icon-192x192.from-favicon.bak
git rm -q addons/web/static/img/odoo-icon-192x192.png.bak
git rm -q addons/web/static/img/odoo-icon-512x512.bak

echo "OK : tous les renommages effectués."
