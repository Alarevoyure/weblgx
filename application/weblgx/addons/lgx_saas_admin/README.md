# Web@LGX — Administration multi-société

Module : `lgx_saas_admin`  
Version : 17.0.1.0.0

## Objectif

Corriger le multi-société trop permissif : un admin local ne doit plus pouvoir
gérer les utilisateurs / sociétés hors de son périmètre.

L’Admin société obtient aussi **Création de contact** (requis pour créer des
utilisateurs et modifier les coordonnées de sa société).

## Rôles

**SuperAdmin** (`lgx_saas_admin.group_superadmin`)

- Compte Administrator (`base.user_admin`)
- Toutes les sociétés, tous les users
- Création / suppression de sociétés
- Apps et Paramètres (implique Settings)

**Admin société** (`base.group_erp_manager` — Droits d'accès)

- Users partageant au moins une de ses sociétés
- Édition de ses sociétés
- Pas de création de société
- Pas Apps / Paramètres globaux

## Comportement

- Un Admin société ne voit que les sociétés de son `company_ids`
- Il ne voit / n’édite que les utilisateurs rattachés à ces sociétés
- Calendrier : « Calendriers de tout le monde » ne montre que les collègues de ses sociétés
- Il ne peut pas assigner une société hors périmètre
- Il ne peut pas attribuer SuperAdmin / Paramètres (Settings)
- Il ne peut pas modifier le compte SuperAdmin
- Seul le SuperAdmin crée ou supprime des sociétés

## Installation

```bash
sudo -u weblgx weblgx -d weblgx -i lgx_saas_admin \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
systemctl restart weblgx
```

### Migration automatique (`post_init_hook`)

1. Assigne SuperAdmin à Administrator et user_root
2. Ajoute toutes les sociétés existantes aux `company_ids` d’Administrator
3. Retire Settings (`group_system`) des autres utilisateurs (ils gardent
   Droits d’accès = Admin société)
4. Lie Création de contact à Droits d’accès

## Vérifications manuelles

1. Se connecter comme admin d’une société (ex. Centre Social…)
2. Paramètres → Utilisateurs : ne doit pas voir les users des autres sociétés
3. Tentative d’ajout d’une société étrangère → refus
4. Tentative de créer une société → refus
5. Se connecter en Administrator : voit tout, peut créer une société

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
