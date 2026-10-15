# Installation Web@LGX

Installe Web@LGX sur une machine **Debian 12 ou 13 amd64** vide : PostgreSQL, les dépendances, l'application déjà présente dans ce kit, la base, les mots de passe, puis le service.

Sur Debian 13, le paquet `python3-pypdf2` n'existe plus. Le script installe un paquet de transition vers `python3-pypdf`. Le binaire wkhtmltopdf est celui construit pour Debian 12 ; il fonctionne aussi sur Debian 13.

À lancer en root, depuis ce répertoire :

```bash
sudo ./install_weblgx
```

Un second lancement conserve les mots de passe déjà générés et ne recrée pas la base.

## Résultat

| Élément | Emplacement |
| --- | --- |
| Configuration | `/etc/weblgx/weblgx.conf` |
| Secrets (root uniquement) | `/root/weblgx-credentials.txt` |
| Application | `/usr/lib/python3/dist-packages/weblgx` |
| Service | `weblgx.service` |
| Commande | `/usr/bin/weblgx` |

La configuration est `/etc/weblgx/weblgx.conf`. 

Connexion : compte `admin`. Le mot de passe est dans le fichier de secrets, ainsi que le mot de passe PostgreSQL du rôle `weblgx` et le mot de passe maître (`admin_passwd`).

## Modules

`etc/modules.list` est la liste des modules installés sur la machine de référence (76 modules). L'application copiée dans le kit ne contient que ceux-là. L'installation les active dans la base, sans en ajouter d'autres.

## Contenu publié

Ce répertoire est le kit public. 
