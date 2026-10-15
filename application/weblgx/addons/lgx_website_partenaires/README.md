# Web@LGX — Bloc Partenaires

Module : `lgx_website_partenaires`  
Version : 17.0.1.0.0  
Catégorie : Website / Website

## À quoi ça sert

Ajoute un bloc d’édition web nommé **Partenaires** : un carrousel de logos
partenaires / clients, avec défilement continu (infini) et options dans
l’éditeur de site.

Aucune donnée n’est stockée dans un modèle métier : le contenu (logos, textes)
est enregistré dans la page du site, donc naturellement isolé en multi-site
(SaaS).

## Dépendances

- `website`
- `lgx_brand_midnight` (couleur de marque `#16213e`)

## Installation

1. Applications → Mettre à jour la liste des applications
2. Rechercher **Web@LGX - Bloc Partenaires**
3. Installer

En ligne de commande (exemple) :

```bash
sudo -u weblgx weblgx -d weblgx -i lgx_website_partenaires \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
```

Puis redémarrer le service si besoin :

```bash
systemctl restart weblgx
```

## Utilisation (éditeur web)

1. Ouvrir une page en mode **Éditer**
2. Dans le panneau des blocs, section **Features**
3. Glisser le bloc **Partenaires** sur la page
4. Personnaliser le titre et le sous-titre
5. Cliquer sur un logo pour le remplacer (média du site)
6. Enregistrer

Mots-clés de recherche dans l’éditeur :
`partenaires`, `partners`, `logos`, `clients`, `carousel`, `carrousel`

## Options du bloc

Sélectionner le bloc Partenaires pour afficher les options :

| Option              | Description                                     |
|---------------------|-------------------------------------------------|
| **Ajouter un logo** | Ajoute un logo (maximum **20**)                 |
| **Supprimer**       | Retire le dernier logo (minimum **1**)          |
| **Vitesse**         | Intervalle du défilement automatique (secondes) |

Réorganiser : glisser-déposer un item logo près d’un autre.

## Comportement du carrousel

- **Desktop** : 6 logos visibles en même temps
- **Tablette large** : 4 logos
- **Tablette** : 3 logos
- **Mobile** : 2 logos
- Si le nombre de logos est inférieur ou égal au nombre visible : pas de
  défilement, flèches masquées
- Si davantage de logos : défilement **infini** (sans rembobinage)
- Flèches précédent / suivant
- Autoplay ; pause au survol
- Logos affichés à taille uniforme (`object-fit: contain`, hauteur ~80 px
  desktop)

Les clones utilisés pour l’effet infini sont purement techniques : ils ne
sont **pas** enregistrés dans le HTML de la page.

## Personnalisation rapide

### Couleur des flèches

Le bloc utilise la variable CSS `--partenaires-accent` (défaut `#16213e`).

### Taille des logos

Dans `static/src/snippets/s_partenaires/000.scss` :

- `--partenaires-logo-height` (ex. `80px`)
- `max-width` des images (ex. `160px`)

### Nombre de logos visibles

Variable CSS `--partenaires-visible` (breakpoints Bootstrap dans le même
fichier SCSS).

Après modification des assets : vider le cache des assets / redémarrer
Web@LGX, puis recharger la page (Ctrl+F5).

## Structure du module

```
lgx_website_partenaires/
├── __manifest__.py
├── __init__.py
├── README.md
├── views/snippets/
│   ├── s_partenaires.xml     # Template du bloc + options éditeur
│   └── snippets.xml          # Enregistrement dans le panneau Features
└── static/src/
    ├── img/snippets_thumbs/s_partenaires.svg
    └── snippets/s_partenaires/
        ├── 000.js            # Carrousel frontend (défilement infini)
        ├── 000.scss          # Styles + responsive
        └── options.js        # Ajouter / supprimer logos (1–20)
```

## Multi-site / SaaS

- Contenu du bloc = HTML de la page du website courant
- Logos uploadés via l’éditeur : soumis à l’isolation des pièces jointes
  (`lgx_website_attachment_isolation`) si ce module est actif
- Aucun enregistrement partagé entre sites

## Dépannage

| Symptôme                     |  Piste                                                                  |
|------------------------------|-------------------------------------------------------------------------|
| Bloc absent de l’éditeur     | Module non installé, ou assets non rechargés (redémarrer / vider cache) |
| Pas de défilement            | Moins de logos que le nombre visible (comportement normal)              |
| Logos de tailles différentes | Préférer des PNG/SVG avec fond transparent ; le cadre reste fixe        |
| Rembobinage visible          | Forcer le rechargement des assets (ancienne version du JS en cache)     |

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
