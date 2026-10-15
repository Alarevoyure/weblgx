from odoo import SUPERUSER_ID, api

_LGX_BRAND_BLUE = "#16213e"
_OBSOLETE_BUTTON_BG = "background-color: #875A7B"
_BUTTON_BG = f"background-color: {_LGX_BRAND_BLUE}"

_INVITATION_INTRO_EN = (
    "Never heard of Web@LGX? It's a professional website creation software "
    "developed by Loégaux. It will considerably improve your experience at "
    "work and increase your productivity."
)
_INVITATION_INTRO_FR = (
    "Vous n'avez jamais entendu parler de Web@LGX ? C'est un logiciel "
    "professionnel pour la création de site Web développé par Loégaux. Il "
    "améliorera considérablement votre expérience au travail et augmentera "
    "votre productivité."
)
_OBSOLETE_INTRO_SNIPPETS = (
    "After signing in, explore your workspace to discover the available features.",
    "Never heard of Odoo? It's an all-in-one business software loved by 7+ million users. "
    "It will considerably improve your experience at work and increase your productivity.",
    "Never heard of Web@LGX? It's an all-in-one business software loved by 7+ million users. "
    "It will considerably improve your experience at work and increase your productivity.",
    "Vous n'avez jamais entendu parler d'Odoo ? C'est un logiciel professionnel tout-en-un "
    "apprécié par plus de 7 millions d'utilisateurs. Il améliorera considérablement votre "
    "expérience au travail et augmentera votre productivité.",
    "Vous n'avez jamais entendu parler d'Web@LGX ? C'est un logiciel professionnel tout-en-un "
    "apprécié par plus de 7 millions d'utilisateurs. Il améliorera considérablement votre "
    "expérience au travail et augmentera votre productivité.",
)


def _replace_button_color(text):
    if not text:
        return text
    return str(text).replace(_OBSOLETE_BUTTON_BG, _BUTTON_BG)


def _replace_intro(text, new_intro):
    if not text or new_intro in text:
        return text
    updated = str(text)
    for snippet in _OBSOLETE_INTRO_SNIPPETS:
        updated = updated.replace(snippet, new_intro)
    return updated


_OBSOLETE_CLOSING_SNIPPETS = {
    "en_US": (
        "Enjoy Odoo!<br>",
        "Enjoy Odoo!<br />",
    ),
    "fr_FR": (
        "Profitez d'Odoo !<br>",
        "Profitez d'Odoo !<br />",
        "Profitez d'Web@LGX !<br>",
        "Profitez d'Web@LGX !<br />",
    ),
}
_CLOSING_SNIPPETS = {
    "en_US": "Enjoy Web@LGX!<br />",
    "fr_FR": "Profitez de Web@LGX !<br>",
}


def _replace_closing(text, lang):
    updated = str(text)
    for snippet in _OBSOLETE_CLOSING_SNIPPETS.get(lang, ()):
        updated = updated.replace(snippet, _CLOSING_SNIPPETS[lang])
    if lang == "fr_FR":
        updated = updated.replace(
            "Profitez d'Web@LGX !",
            "Profitez de Web@LGX !",
        )
    return updated


def patch_invitation_email_intro(env):
    """Met à jour le paragraphe d'introduction de l'e-mail d'invitation utilisateur."""
    template = env.ref("auth_signup.set_password_email", raise_if_not_found=False)
    if not template:
        return

    updates = {
        "en_US": _INVITATION_INTRO_EN,
        "fr_FR": _INVITATION_INTRO_FR,
    }
    for lang, new_intro in updates.items():
        current = template.with_context(lang=lang).body_html or ""
        new_body_html = _replace_button_color(
            _replace_closing(_replace_intro(current, new_intro), lang)
        )
        if new_body_html != str(current):
            template.with_context(lang=lang).sudo().write({"body_html": new_body_html})


def patch_signup_email_button_colors(env):
    """Remplace le violet Odoo par le bleu Web@LGX sur les boutons des e-mails."""
    xmlids = (
        "auth_signup.set_password_email",
        "auth_signup.mail_template_user_signup_account_created",
    )
    for xmlid in xmlids:
        template = env.ref(xmlid, raise_if_not_found=False)
        if not template:
            continue
        for lang in ("en_US", "fr_FR"):
            current = template.with_context(lang=lang).body_html or ""
            new_body_html = _replace_button_color(current)
            if new_body_html != str(current):
                template.with_context(lang=lang).sudo().write({"body_html": new_body_html})


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    patch_invitation_email_intro(env)
    patch_signup_email_button_colors(env)
