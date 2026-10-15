# Web@LGX — Administration multi-société

Module : `lgx_saas_admin`  
Version : 17.0.1.1.0

## Objectif

Deux niveaux d'administration, avec les mêmes menus et les mêmes droits techniques.

## Rôles

**SuperAdmin** (`lgx_saas_admin.group_superadmin`)

- Comptes Administrator et OdooBot
- Voit et administre toutes les sociétés
- Création et suppression de sociétés
- Membre de toutes les sociétés (sélecteur inclus)

**Admin** (`base.group_system`, libellé Admin)

- Mêmes droits d'administration (Paramètres, utilisateurs, site, wiki)
- Uniquement les sociétés autorisées (`company_ids` de l'utilisateur)
- Pas de création ni de suppression de société
- Ne peut pas attribuer SuperAdmin ni modifier un compte SuperAdmin

**Droits d'accès** (`base.group_erp_manager`)

- Gestion des utilisateurs de ses sociétés, sans le niveau Admin

## Installation / mise à jour

```bash
sudo -u weblgx weblgx -d weblgx -u lgx_saas_admin \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
systemctl restart weblgx
```

Au premier passage, les SuperAdmin autres qu'Administrator et OdooBot
deviennent Admin et conservent leurs sociétés autorisées.

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
