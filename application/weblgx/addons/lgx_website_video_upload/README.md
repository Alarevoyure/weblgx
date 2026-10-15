# Web@LGX — Upload vidéo

Module : `lgx_website_video_upload`

## À quoi ça sert

Ajoute un onglet **Uploaded videos / Vidéos uploadées** dans le sélecteur
de médias du site, à côté de l’onglet Vidéos (YouTube / Vimeo…).

Formats : mp4, webm, ogg, mov, avi, mkv.

Le fichier est stocké en pièce jointe (`ir.attachment`), isolé par site
via `lgx_website_attachment_isolation`.

## Installation

```bash
sudo -u weblgx weblgx -d weblgx -i lgx_website_video_upload \
  --config /etc/weblgx/weblgx.conf --stop-after-init --no-http
systemctl restart weblgx
```

## Utilisation

1. Éditer une page
2. Insérer un média / bloc Vidéo / remplacer un média
3. Onglet **Uploaded videos**
4. **Upload a video** → choisir le fichier → la vidéo native est insérée

## Licence

LGPL-3 — LOEGAUX / Ferme 201 SARL
