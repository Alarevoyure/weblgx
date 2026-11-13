#!/usr/bin/env python3
# Renommage de contenu : odoo/Odoo/ODOO -> weblgx/Web@LGX/WEBLGX
# dans tous les fichiers texte de application/weblgx (fichiers binaires exclus).

import os
import re

ROOT = '/root/weblgx/application/weblgx'

SKIP_EXTS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.bmp', '.tiff',
    '.woff', '.woff2', '.ttf', '.otf', '.eot',
    '.pyc', '.pyo', '.map', '.db', '.sqlite', '.dump',
    '.gz', '.bz2', '.xz', '.zip', '.tgz', '.whl', '.deb',
    '.swp', '.bak', '.swo', '.mo', '.fodt', '.docx', '.xlsx', '.pdf',
}


def is_text(path):
    base = os.path.basename(path)
    if base == 'LICENSE' or base.startswith('LICENSE') or base == 'COPYING':
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in SKIP_EXTS:
        return False
    return True


REPLACEMENTS = [
    # odoo (minuscule, token) -> weblgx
    (re.compile(r'(?<![A-Za-z0-9_])odoo(?![A-Za-z0-9])'), 'weblgx'),
    # Odoo (branding) -> Web@LGX
    (re.compile(r'(?<![A-Za-z0-9_])Odoo(?![A-Za-z0-9])'), 'Web@LGX'),
    # ODOO (constantes/env) -> WEBLGX
    (re.compile(r'(?<![A-Za-z0-9_])ODOO(?![A-Za-z0-9])'), 'WEBLGX'),
    # Identifiants concaténés / camelCase
    ('odoobot', 'weblgxbot'),
    ('OdooBot', 'WeblgxBot'),
    ('odooEditor', 'weblgxEditor'),
    ('OdooEditor', 'WeblgxEditor'),
    ('ZoomOdoo', 'ZoomWeblgx'),
    ('zoomodoo', 'zoomweblgx'),
    ('is_odoo_module', 'is_weblgx_module'),
    ('get_aliased_odoo_define_content', 'get_aliased_weblgx_define_content'),
    ('__odoo', '__weblgx'),
]

changed_files = 0
total_substitutions = 0
skipped = 0

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d != '__pycache__']
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        if not is_text(p):
            skipped += 1
            continue
        try:
            with open(p, 'r', encoding='utf-8', errors='surrogateescape') as f:
                content = f.read()
        except Exception as e:
            print('SKIP (read):', p, e)
            continue
        new = content
        file_subs = 0
        for pat, repl in REPLACEMENTS:
            if hasattr(pat, 'subn'):
                new, n = pat.subn(repl, new)
            else:
                n = new.count(pat)
                new = new.replace(pat, repl)
            file_subs += n
        if new != content:
            try:
                with open(p, 'w', encoding='utf-8', errors='surrogateescape') as f:
                    f.write(new)
            except Exception as e:
                print('SKIP (write):', p, e)
                continue
            changed_files += 1
            total_substitutions += file_subs

print('fichiers modifiés :', changed_files)
print('substitutions totales :', total_substitutions)
print('fichiers binaires/ignorés :', skipped)
