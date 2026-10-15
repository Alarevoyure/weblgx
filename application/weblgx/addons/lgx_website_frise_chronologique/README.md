# Web@LGX — Frise chronologique

Module : `lgx_website_frise_chronologique`

Bloc vertical : **icône** | **ligne + pastille** | **date + texte**.

## Installation

```bash
sudo -u weblgx weblgx -d weblgx -i lgx_website_frise_chronologique \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
systemctl restart weblgx
```

## Utilisation

1. Éditer une page → **Frise Chronologique** (près de Timeline / Ligne du temps)
2. Cliquer une icône pour la changer (média / Font Awesome)
3. Éditer date et description
4. Options du bloc : Ajouter / Supprimer un événement, couleur de la frise

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
