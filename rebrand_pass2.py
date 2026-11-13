#!/usr/bin/env python3
# Seconde passe : remplace les occurrences restantes (identifiants concaténés/camelCase)
# odoo -> weblgx et Odoo -> Weblgx sur tous les fichiers texte.

import os

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


changed = 0
subs = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d != '__pycache__']
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        if not is_text(p):
            continue
        try:
            with open(p, 'r', encoding='utf-8', errors='surrogateescape') as f:
                content = f.read()
        except Exception:
            continue
        new = content
        n = 0
        new = new.replace('Odoo', 'Weblgx')
        n += new.count('Weblgx') - content.count('Weblgx')
        new = new.replace('odoo', 'weblgx')
        n += new.count('weblgx') - content.count('weblgx')
        new = new.replace('ODOO', 'WEBLGX')
        if new != content:
            with open(p, 'w', encoding='utf-8', errors='surrogateescape') as f:
                f.write(new)
            changed += 1
            subs += n
print('fichiers modifiés :', changed)
print('substitutions :', subs)
