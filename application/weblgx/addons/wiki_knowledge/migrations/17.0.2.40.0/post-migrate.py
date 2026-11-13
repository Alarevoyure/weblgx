# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Ouvre l'accès public aux articles en état « Modifié » (image tuile / article)."""
    from weblgx import api, SUPERUSER_ID
    from weblgx.addons.wiki_knowledge.hooks import patch_gallery_public_access_rules

    env = api.Environment(cr, SUPERUSER_ID, {})
    patch_gallery_public_access_rules(env)
