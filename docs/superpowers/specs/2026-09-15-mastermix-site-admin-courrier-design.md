# mastermix.fr — backoffice de contenu et courrier

Date : 2026-09-15. Statut : validé section par section en discussion, spec soumis à relecture.

## 1. Objet

Remplacer le site statique mastermix.fr (nginx sur `192.168.1.166:8095`) par un serveur Python autonome qui :

1. sert la page publique validée aujourd'hui, à l'identique, à partir d'un contenu éditable ;
2. offre un backoffice `/admin` pour modifier les sections, créer des pages libres et gérer les fichiers téléchargeables ;
3. lit et envoie du courrier pour toutes les boîtes `@mastermix.fr` et crée ces boîtes, en s'appuyant sur Mailu (.166).

Patron : `karakal.media` (serveur `http.server` de la bibliothèque standard, contenu JSON, backoffice `/admin`, courrier IMAP/SMTP vers Mailu). Aucune dépendance à installer.

Hors périmètre : formulaire de contact public, calendrier, contacts, filtres de courrier, multi-comptes admin, éditeur WYSIWYG.

## 2. Architecture

```
Internet ── Freebox 80/443 ── nginx .117 (TLS mastermix.fr, inchangé) ── 192.168.1.166:8095
                                                                             │
                                                    conteneur mastermix-site (python:3.12-alpine)
                                                    /mnt/karakalia/mastermix-site/
                                                      app/      code (lecture seule)
                                                      data/     contenu, pages, réglages, journal, sauvegardes
                                                      www/      logo, captures, media/, telechargements/
                                                                             │ IMAP 993 / SMTP 465 / API HTTP
                                                    Mailu (.166) : domaine mastermix.fr, boîtes, DKIM
```

Code dans le dépôt MasterMix, dossier `site/app/` :

| Fichier | Rôle |
|---|---|
| `server.py` | Serveur HTTP (ThreadingHTTPServer), routage public et admin, sessions, CSRF, limites |
| `render.py` | Génération HTML de la page publique et des pages libres à partir du contenu |
| `markdown_lite.py` | Conversion du Markdown simplifié des pages libres en HTML sûr |
| `store.py` | Lecture/écriture JSON atomique sous verrou, sauvegardes horodatées, restauration |
| `admin.py` | Compte admin (pbkdf2), sessions, blocage après échecs, journal |
| `admin_ui.py` | HTML/CSS/JS du backoffice (statique, sans dépendance externe) |
| `secrets_box.py` | Chiffrement des mots de passe de boîtes au repos (clé locale `data/.cle`) |
| `courrier.py` | IMAP (liste, lecture, marquer, supprimer) et SMTP (envoi, copie dans Envoyés) |
| `mailu_api.py` | Client HTTP de l'API Mailu : boîtes, alias, mot de passe |
| `tests/` | Tests unitaires (unittest) |

Chaque module a une responsabilité unique et s'utilise sans connaître les autres : `courrier.py` reçoit des réglages et renvoie des dictionnaires ; `mailu_api.py` ne connaît que l'URL et le jeton ; `render.py` ne lit pas le disque.

## 3. Contenu et pages

### 3.1 Données

`data/content.json` : la page publique découpée en sections, chaque champ texte éditable.

```json
{
  "site": {"titre": "MasterMix", "description": "...", "contact": "contact@mastermix.fr"},
  "accueil": {"surtitre": "...", "titre": "MasterMix", "accroche": "...", "accroche_mot": "facile",
              "bouton": "Télécharger pour Windows", "meta": "Gratuit · Version 9.8.24 · ...",
              "capture": "editeur.jpg", "legende": "..."},
  "promesses": {"titre": "...", "sous_titre": "...",
                "cartes": [{"titre": "Facile", "texte": "..."}, ...]},
  "console": {"surtitre": "...", "titre": "...", "texte": "...", "capture": "mixer.jpg", "points": ["...", "..."]},
  "telechargement": {"titre": "...", "texte": "...", "fichier": "MasterMix-9.8.24-Setup-x64.exe",
                     "taille": 68120243, "sha256": "c104...", "note": "..."},
  "configuration": {"titre": "...", "texte": "...", "lignes": [["Système", "Windows 10 ou 11, 64 bits"], ...]},
  "pied": {"signature": "...", "licence": "..."}
}
```

`data/pages/<slug>.json` : `{"slug", "titre", "contenu_md", "visible", "ordre", "cree", "modifie"}`. Slug : minuscules, chiffres, tirets, 1 à 60 caractères, unique.

### 3.2 Rendu

- `GET /` : page validée aujourd'hui (même CSS, même structure), remplie depuis `content.json`. Le menu ajoute les pages visibles, triées par `ordre`.
- `GET /p/<slug>` : page libre avec la même en-tête, le même pied et la même feuille de style ; corps rendu par `markdown_lite`.
- Markdown simplifié : `#`/`##`/`###`, paragraphes, `**gras**`, `*italique*`, listes `-`, liens `[texte](url)`, images `![alt](media/x.jpg)`, lignes `---`. Tout le reste est échappé ; les URL acceptées commencent par `http://`, `https://`, `/`, `mailto:`.
- Aucun cache : chaque requête relit le JSON (fichiers de quelques Ko).
- Fichiers statiques : `www/` servi tel quel ; `www/telechargements/` en pièce jointe avec `Accept-Ranges`, sans listing ; `SHA256SUMS.txt` régénéré à chaque téléversement.

### 3.3 Fichiers

- Images (`png`, `jpg`, `webp`, `svg` assaini) jusqu'à 8 Mo dans `www/media/`, nom assaini, unicité par suffixe.
- Installeurs (`exe`, `zip`, `msi`) jusqu'à 200 Mo dans `www/telechargements/`, téléversement par morceaux de 1 Mo, SHA-256 et taille calculés côté serveur et proposés pour remplir la section Téléchargement.
- Suppression avec confirmation ; un fichier référencé par le contenu ne se supprime pas.

### 3.4 Sauvegardes

Chaque écriture de `content.json` ou d'une page : fichier temporaire puis `os.replace`, sous verrou, puis copie horodatée dans `data/backups/` (30 dernières conservées). Onglet Réglages : liste des sauvegardes, restauration en un clic (elle-même sauvegardée avant).

## 4. Admin et sécurité

- `/admin` : un compte, mot de passe pbkdf2-sha256 (200 000 itérations, sel 16 octets) dans `data/admin.json`. Au premier démarrage sans `admin.json` : mot de passe aléatoire de 16 caractères, écrit une fois dans le journal du conteneur (`docker logs`). Changement dans Réglages (ancien + nouveau, 12 caractères minimum).
- Blocage : 5 échecs en 15 minutes par IP (X-Real-IP fourni par le relais .117) bloquent 15 minutes.
- Session : cookie `mm_session`, jeton 32 octets aléatoires, `HttpOnly; Secure; SameSite=Strict`, expiration 12 h d'inactivité, une seule session active. Variable `MM_DEV=1` retire `Secure` en développement local uniquement.
- CSRF : jeton par session, exigé dans l'en-tête `X-CSRF` sur toute requête POST/PUT/DELETE de l'admin ; comparaison en temps constant.
- Limites : corps 512 Ko sauf téléversements ; téléversements en morceaux avec taille cumulée vérifiée.
- Secrets : `data/settings.json` (jeton API Mailu, boîtes et mots de passe chiffrés) en mode 600 ; clé de chiffrement `data/.cle` (32 octets, mode 600) générée au premier démarrage. La bibliothèque standard n'offre pas de chiffrement authentifié ; choix : chiffrement de flux construit sur `hashlib`/`hmac` (clé de chiffrement et clé d'authentification dérivées de `data/.cle` par HKDF-SHA256, flux SHA-256 en mode compteur avec nonce aléatoire de 16 octets, XOR, puis étiquette HMAC-SHA256 vérifiée avant déchiffrement). Protège contre la lecture du fichier hors du conteneur ; ne protège pas contre un attaquant qui a la clé et le fichier (même volume), ce qui est accepté et documenté. Les mots de passe ne sont jamais renvoyés au navigateur.
- Journal `data/journal.log` : horodatage, IP, action (connexion, échec, modification de section, page, fichier, envoi de message, création/suppression de boîte). Consultable dans Réglages (200 dernières lignes), rotation à 1 Mo.
- Interface : onglets Contenu, Pages, Fichiers, Courrier, Adresses, Réglages. HTML servi par `admin_ui.py`, JavaScript minimal (fetch + formulaires), aucune ressource externe.

## 5. Courrier et adresses

### 5.1 Mailu

- Domaine `mastermix.fr` créé le 2026-09-15 (`config-import`, clé DKIM générée, 50 boîtes, 50 alias). DNS MX/SPF/DKIM/DMARC publiés chez IONOS et vérifiés.
- API : `API=true` et `API_TOKEN=<aléatoire 32 octets hex>` ajoutés à `mailu.env`, redémarrage du conteneur `admin` de Mailu uniquement. L'API répond sur le réseau interne Mailu ; le conteneur `mastermix-site` la joint par `http://192.168.1.166:8080/api/v1/` (port 8080 du front Mailu, déjà exposé sur le LAN) avec l'en-tête `Authorization: Bearer <jeton>`. Le jeton est saisi une fois dans Réglages.

### 5.2 Onglet Adresses

- Liste des boîtes `@mastermix.fr` (API `GET /user`, filtrée sur le domaine) : adresse, nom, quota, état « ouvrable depuis l'admin » (mot de passe connu).
- Créer : adresse (partie locale validée `[a-z0-9._-]{1,64}`), nom affiché, mot de passe généré (16 caractères) ou saisi (12 minimum), quota (défaut 1 Go). `POST /user`. Le mot de passe est chiffré et rangé dans `settings.json`.
- Réinitialiser le mot de passe : `PATCH /user/<adresse>` avec un nouveau mot de passe ; mise à jour de la copie chiffrée.
- Rattacher une boîte existante : saisie du mot de passe, vérifié par une connexion IMAP avant enregistrement.
- Supprimer : confirmation par saisie de l'adresse ; `DELETE /user/<adresse>` ; retrait de la copie chiffrée.
- Alias : liste, création (`POST /alias`, ex. `support@` vers `contact@`), suppression.

### 5.3 Onglet Courrier

- Sélecteur de boîte parmi celles « ouvrables ». Dossiers `INBOX` et `Sent`.
- Liste : 60 derniers messages (`imaplib`, `FETCH ENVELOPE FLAGS RFC822.SIZE`), expéditeur, objet, date, lu/non lu, pièce jointe oui/non. Rafraîchissement manuel.
- Lecture : texte brut, ou HTML assaini (balises et attributs autorisés, images distantes bloquées par défaut), pièces jointes téléchargeables (nom assaini, taille affichée).
- Actions : marquer lu/non lu, supprimer (`\Deleted` + `EXPUNGE`), répondre, transférer.
- Connexion IMAP : `192.168.1.166:993`, contexte TLS par défaut, nom de certificat `mail.besancon.vip` (même mécanisme que `karakal.media/courrier.py`), délai 12 s. Pannes remontées en clair dans l'admin (« serveur injoignable », « identifiants refusés »).

### 5.4 Envoi

- Nouveau message, réponse (`In-Reply-To`/`References`, objet préfixé « Re: », citation du texte), transfert (« Fwd: », pièces jointes reprises).
- Champs : De (boîte choisie, nom affiché), À/Cc (adresses validées), Objet, Texte (brut ; HTML non édité), pièces jointes jusqu'à 20 Mo au total.
- SMTP : `192.168.1.166:465` en SMTPS, authentification avec les identifiants de la boîte, même vérification de certificat que l'IMAP. Après envoi, copie dans `Sent` via `APPEND`. Mailu signe DKIM.
- Journal : destinataire(s), objet, boîte, résultat.

## 6. DNS (fait)

| Type | Nom | Valeur |
|---|---|---|
| A | `@`, `www` | `82.66.209.160` |
| MX | `@` | `10 mail.besancon.vip` |
| TXT | `@` | `v=spf1 ip4:82.66.209.160 -all` |
| TXT | `dkim._domainkey` | `v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA6kNF…wIDAQAB` (clé Mailu, 408 caractères) |
| TXT | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:postmaster@mastermix.fr` |

Vérifié le 2026-09-15 sur les quatre serveurs IONOS et sur 1.1.1.1/8.8.8.8. Passage à `p=reject` quand la délivrabilité est confirmée.

## 7. Déploiement

- `/mnt/karakalia/mastermix-site/docker-compose.yml` : service `web`, image `python:3.12-alpine`, commande `python3 /app/server.py`, `ports: 192.168.1.166:8095:8095`, volumes `./app:/app:ro`, `./data:/data`, `./www:/www`, variables `MM_HOST=0.0.0.0`, `MM_PORT=8095`, `MM_DATA=/data`, `MM_WWW=/www`, `MM_SITE_URL=https://mastermix.fr`, `restart: unless-stopped`. Utilisateur non root dans le conteneur (`user: "1000:1000"`), `data/` et `www/` possédés par cet UID.
- `site/deploy.sh 166` : envoie `site/app/`, `site/www/` (sans les installeurs déjà en place) et le compose, puis `docker compose up -d --force-recreate`. L'ancien `nginx.conf` reste dans le dossier pour rollback (`docker-compose.nginx.yml`).
- Relais .117 : inchangé (`proxy_pass http://192.168.1.166:8095`, `proxy_buffering off`, `client_max_body_size` à passer de 1 Mo à 2 Mo pour les morceaux de téléversement de 1 Mo ; les pièces jointes de 20 Mo passent en morceaux aussi).
- Migration : au premier démarrage sans `content.json`, le serveur écrit le contenu de la page actuelle (valeurs codées dans `render.py` comme défaut) ; la page publique reste identique.
- Mailu : ajout `API=true`/`API_TOKEN` dans `mailu.env` puis `docker compose up -d admin` dans `/mnt/karakalia/mailu`. Vérification `curl -H "Authorization: Bearer …" http://192.168.1.166:8080/api/v1/domain`.

## 8. Tests

Unitaires (`python -m unittest discover site/app/tests`), sans réseau :

- `render` : page publique générée depuis le contenu par défaut identique (à l'espace près) à `site/www/index.html` actuel ; menu avec pages visibles triées ; échappement des champs.
- `markdown_lite` : chaque construction, injection HTML échappée, URL refusées (`javascript:`), images limitées à `media/`.
- `store` : écriture atomique, sauvegarde horodatée, rotation à 30, restauration.
- `admin` : hachage/vérification, blocage après 5 échecs, expiration de session, CSRF.
- `secrets_box` : chiffrer/déchiffrer, altération détectée, clé différente refusée.
- `courrier` : parsing d'un message multipart (texte, HTML assaini, pièces jointes), construction d'une réponse et d'un transfert ; IMAP/SMTP simulés par des doubles.
- `mailu_api` : requêtes attendues (méthode, chemin, corps, en-tête) contre un serveur HTTP factice local ; gestion des erreurs 401/404/409.

Recette en production, dans l'ordre :

1. `curl https://mastermix.fr/` identique à l'ancienne page (diff HTML normalisé).
2. Connexion admin avec le mot de passe initial, changement de mot de passe.
3. Modifier l'accroche, vérifier en ligne ; restaurer la sauvegarde précédente.
4. Créer une page « Actualités » visible, la voir dans le menu ; la masquer.
5. Téléverser une image, l'insérer dans la page ; téléverser l'installeur courant, empreinte identique à l'actuelle.
6. Saisir le jeton Mailu ; créer `contact@mastermix.fr` ; l'ouvrir dans Courrier.
7. Envoyer un message vers une adresse Gmail : en-têtes `spf=pass dkim=pass dmarc=pass`.
8. Répondre depuis Gmail ; le message apparaît dans l'admin ; y répondre.
9. Créer un alias `support@` vers `contact@`, envoyer à `support@`, réception dans `contact@`.
10. Redémarrer le conteneur : sessions expirées, données intactes.

## 9. Rollback

- Site : `docker compose -f docker-compose.nginx.yml up -d` remet le nginx statique ; `www/` est resté servi tel quel.
- Mailu : retirer `API=true`/`API_TOKEN`, `docker compose up -d admin`. Le domaine et les boîtes restent.
- Données : `data/` suffit à restaurer l'ensemble (contenu, pages, réglages, journal).

## 10. Décisions et hypothèses

- Bibliothèque standard uniquement, comme karakal.media : rien à installer sur le NAS.
- Mots de passe de boîtes conservés chiffrés localement : c'est ce qui permet d'ouvrir toutes les boîtes depuis l'admin (choix validé). Limite documentée : quiconque a accès au volume Docker a la clé et le fichier.
- Un seul compte admin, une seule session : suffisant pour un site vitrine.
- L'API Mailu est jointe sur le port 8080 du front Mailu déjà exposé sur le LAN ; si l'API n'y répond pas (routage front), repli sur le port interne du conteneur admin via le réseau Docker de Mailu, à vérifier au déploiement.
- `contact@mastermix.fr` n'existe pas encore ; elle est créée à l'étape 6 de la recette, ce qui rend l'adresse du pied de page valide.
