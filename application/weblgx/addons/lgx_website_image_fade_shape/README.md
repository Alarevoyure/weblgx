# Web@LGX — Forme image fondu

Module : `lgx_website_image_fade_shape`

Ajoute une catégorie **Fondu** dans le sélecteur de formes d’image
(onglet Decorative) :

- Fondu gauche (comme l’exemple fourni)
- Fondu droite
- Fondu haut
- Fondu bas
- Fondu latéral (deux côtés)

Le fondu rend progressivement l’image transparente vers le bord :
sur un fond blanc, l’effet correspond à un dégradé blanc.

## Installation

```bash
sudo -u weblgx weblgx -d weblgx -i lgx_website_image_fade_shape \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
systemctl restart weblgx
```

## Utilisation

1. Éditer une page, sélectionner une image
2. Option **Shape** → Decorative → **Fondu**
3. Choisir la direction

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
