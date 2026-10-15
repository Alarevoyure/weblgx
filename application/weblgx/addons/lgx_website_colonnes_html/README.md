# Web@LGX — Colonnes HTML

Module : `lgx_website_colonnes_html`
Version : 17.0.1.0.0

## À quoi ça sert

Ajoute un bloc **Colonnes HTML** dans l’éditeur de pages :

- de **1 à 6** colonnes côte à côte
- chaque colonne contient du **code HTML**
- édition via un éditeur Ace (comme Embed Code)

Le contenu est stocké dans le HTML de la page du site courant
(isolation multi-site / SaaS, aucune table métier partagée).

## Dépendances

- `website`
- `lgx_brand_midnight` (accent `#16213e`)

## Installation

```bash
sudo -u weblgx weblgx -d weblgx -i lgx_website_colonnes_html \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
systemctl restart weblgx
```

## Utilisation

1. Éditer une page
2. Blocs → **Colonnes HTML** (près de Embed Code)
3. Sur le bloc : choisir le nombre de colonnes (1–6)
4. Cliquer une colonne → **Modifier le code** → coller le HTML → Enregistrer

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
