# Web@LGX — Bloc Colonnes Editables

Module : lgx_website_colonnes_editables
Version : 17.0.1.0.0
Catégorie : Website / Website

## À quoi ça sert

Ajoute un bloc d’édition web nommé **Colonnes Editables**, basé sur le concept
du bloc Colonnes, avec des options supplémentaires :

- curseur de taille d’image (25 % à 100 %)
- largeur et hauteur de chaque colonne
- zone texte scindée (texte à gauche, image/icône à droite) avec largeur
  de la zone média réglable

Aucune donnée n’est stockée dans un modèle métier : le contenu est enregistré
dans la page du site (isolation multi-site / SaaS).

## Dépendances

- website
- lgx_brand_midnight (couleur de marque #16213e)

## Installation

1. Applications → Mettre à jour la liste des applications
2. Rechercher Web@LGX - Bloc Colonnes Editables
3. Installer

En ligne de commande ::

    sudo -u weblgx weblgx -d weblgx -i lgx_website_colonnes_editables \
      --config /etc/weblgx/weblgx.conf --stop-after-init --no-http

Puis redémarrer le service si besoin ::

    systemctl restart weblgx

## Utilisation

1. Éditer une page
2. Panneau des blocs, à côté de Columns / Colonnes
3. Glisser Colonnes Editables
4. Options selon la sélection :

   - Image → curseur Taille image (25–100 %)
   - Colonne → Largeur colonne / Hauteur colonne
   - Zone texte / média → Largeur zone média

## Multi-site / SaaS

Contenu = HTML de la page du website courant. Aucun enregistrement partagé
entre sites.

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
