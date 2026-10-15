# -*- coding: utf-8 -*-

def post_init_hook(env):
    """Assign a website to legacy events and align company_id."""
    Website = env["website"].sudo()
    Event = env["event.event"].sudo()

    csmanduel = Website.search([("name", "ilike", "CSMANDUEL")], limit=1)
    fete = Event.search([("name", "ilike", "Fete de la musique")], limit=1)
    if fete and csmanduel:
        fete.write({
            "website_id": csmanduel.id,
            "company_id": csmanduel.company_id.id,
        })

    for event in Event.search([("website_id", "=", False)]):
        website = Website.search([("company_id", "=", event.company_id.id)], limit=1)
        if not website:
            website = Website.search([], limit=1)
        if website:
            event.write({
                "website_id": website.id,
                "company_id": website.company_id.id,
            })
