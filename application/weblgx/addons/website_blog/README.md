# Blog

Articles de site web, isolés par site et par société (mode SaaS).

Chaque blog, article, étiquette et catégorie d'étiquettes appartient à un seul `website_id`. La société est celle du site. Un visiteur ne voit que le site en cours. En backend, Configuration → Blog n'affiche que le site de la société active.

Les pages du blog reprennent le thème du site. La couleur de marque est le bleu nuit `#16213e`, défini dans `lgx_brand_midnight`. Le bouton « Nouveau » des concepteurs reprend cette couleur.

Un concepteur du site voit ce bouton sur la page du blog. Il crée un brouillon sur le blog du site en cours et ouvre l'éditeur.

## Commentaires

Un visiteur non connecté laisse un commentaire avec son adresse email et son message. Un code à 6 chiffres lui est envoyé par email. Après confirmation du code, le commentaire reste masqué tant qu'un concepteur du site, membre de la société du blog, ne l'a pas validé. Sous l'article, cet administrateur voit les commentaires en attente et peut les valider ou les refuser.

## PlexiPost

Chaque site a son propre Client ID, son Secret et son blog de destination. Le réglage est dans Site Web → Configuration → Paramètres, bloc PlexiPost. L'adresse du récepteur est aussi affichée sur la fiche du site.

PlexiPost envoie un POST JSON sur https://www.exemple.fr/blog/plexipost/receive

En-têtes : Content-Type application/json, X-Client-Id, X-Client-Secret. Un en-tête Authorization Basic avec client_id:secret est accepté à la place.

Corps JSON : post_id, title, body_html, body_text, image_base64, image_mime, image_filename. title est le titre de l'article. Le texte vient de body_html, sinon de body_text. Le titre n'est pas répété dans le texte. L'image, si elle est jointe et fait moins de 4 Mo, est placée sous le texte et sert aussi de fond au titre, assombri pour garder le titre lisible. Sans published, l'article reste un brouillon. Le même post_id met à jour l'article. La réponse JSON contient id, url, published et created.

Licence : LGPL-3 — LOEGAUX / Ferme 201 SARL
