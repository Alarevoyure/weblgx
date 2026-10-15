# Web@LGX

Web@LGX est une application pour créer des sites web, avec un wiki intégré aux pages du site. Le wiki va au-delà d'une simple base d'articles : les pages se rédigent depuis le site, s'organisent dans la navigation, et suivent un circuit de relecture côté administration.

Chaque site reste isolé. Plusieurs sites peuvent coexister sur la même installation, avec leurs propres pages, leurs contenus et leurs accès.

## Sites web

Les pages se composent dans l'éditeur du site : textes, colonnes, images, vidéos, blocs réutilisables, partenaires, frises chronologiques. Le site publié et l'administration sont distincts. Les visiteurs voient le site ; la rédaction et les réglages se font dans l'interface d'administration.

## Wiki

Le wiki fait partie du site, pas d'un outil séparé.

- Rédaction des articles depuis le site.
- Sommaire, galerie, derniers articles et articles les plus consultés, insérables dans les pages.
- Rôles de relecture : rédacteur, relecteur, gestionnaire du wiki.
- Chaque article appartient à un site. Un autre site de la même installation ne le voit pas.

## Installation

Machine **Debian 12 ou 13**, architecture **amd64**, de préférence vide. L'installation se fait en root. Elle installe PostgreSQL, les dépendances, l'application, la base et le service. Compter plusieurs minutes.

```bash
git clone https://github.com/Alarevoyure/weblgx.git
cd weblgx
sudo ./install_weblgx
```

À la fin, l'écran affiche l'adresse (`http://<adresse-du-serveur>:7069`), le compte `admin` et son mot de passe. Les mêmes informations sont enregistrées dans `/root/weblgx-credentials.txt`, lisible seulement par root. Ce fichier n'est pas dans le dépôt : les mots de passe sont créés sur la machine pendant l'installation.

Un second lancement conserve ces mots de passe. Il ne recrée pas la base si le site est déjà installé.

## Après l'installation

| Élément | Emplacement |
| --- | --- |
| Adresse | `http://<adresse-du-serveur>:7069` |
| Compte | `admin` |
| Mots de passe | `/root/weblgx-credentials.txt` |
| Configuration | `/etc/weblgx/weblgx.conf` |
| Service | `systemctl status weblgx` |
| Commande | `/usr/bin/weblgx` |

La configuration utilisée est `/etc/weblgx/weblgx.conf`.
