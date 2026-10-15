# Web@LGX — Bloc de blocs

Module : `lgx_website_bloc_de_blocs`

## À quoi ça sert

Bloc **Colonnes** (1 à 6) dont chaque colonne est une zone `oe_structure` :
on peut y **déposer d’autres blocs** du site (texte, image, vidéo, Colonnes HTML…).

Même principe que les onglets (Tabs) de Weblgx.

## Installation

```bash
sudo -u weblgx weblgx -d weblgx -i lgx_website_bloc_de_blocs \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
systemctl restart weblgx
```

## Utilisation

1. Éditer une page → glisser **Bloc de blocs**
2. Choisir le nombre de colonnes (1–6)
3. Glisser des blocs **dans** chaque colonne (zone en pointillés)

## Multi-site

Contenu = HTML de la page du website courant. Aucune table métier partagée.

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
