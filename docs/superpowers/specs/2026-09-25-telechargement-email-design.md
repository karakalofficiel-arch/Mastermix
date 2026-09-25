# mastermix.fr — téléchargement contre e-mail confirmé

Date : 2026-09-25 · Statut : spec à relire par Ahmed · Auteur : Claude pour Ahmed Hadjadj

## Objectif

Savoir qui télécharge MasterMix. Pour obtenir l'installeur, une personne donne son
e-mail et le confirme en cliquant un lien personnel reçu par e-mail. La liste est
consultable dans le backoffice. **Aucun envoi ultérieur** : l'adresse sert
uniquement à savoir qui télécharge.

## Décisions d'Ahmed

- But : une liste consultable dans le backoffice, sans lettre d'information.
- Verrou : lien personnel valable 7 jours. L'adresse brute du fichier
  (`/telechargements/MasterMix-<v>-Setup-x64.exe`) n'est plus liée depuis le site,
  mais reste servie pour la mise à jour automatique des versions installées
  (manifeste `/maj/mastermix2.json`). Contournable par un initié : accepté.
- Expéditeur : `contact@mastermix.fr`, à créer sur Mailu (aucune adresse
  `@mastermix.fr` n'existe au 2026-09-25) et à rattacher au site.

## 1. Parcours

1. Les deux boutons « Télécharger » de la page (bandeau d'accueil et section
   Téléchargement) mènent à `#telechargement`. La section contient un formulaire
   (`POST /telechargement/demande`, formulaire HTML classique, sans JavaScript
   obligatoire) :
   - champ e-mail (obligatoire) ;
   - champ piège `site_web` invisible (masqué en CSS, `tabindex=-1`,
     `autocomplete=off`) : s'il est rempli, on répond comme si tout allait bien et
     on n'envoie rien ;
   - phrase d'information : « Votre adresse sert uniquement à savoir qui télécharge
     MasterMix. Aucun envoi ultérieur. Conservée jusqu'à votre demande de suppression, à
     contact@mastermix.fr. »
2. Réponse : page « Vérifiez votre boîte » (même gabarit que le site) : « Un e-mail
   vient d'être envoyé à <adresse>. Le lien qu'il contient est valable 7 jours. »
   Même réponse si l'adresse est déjà confirmée (un nouveau lien est envoyé).
3. E-mail (texte brut, français), de `MasterMix <contact@mastermix.fr>`, sujet
   « Votre lien de téléchargement MasterMix » : bonjour, le lien
   `https://mastermix.fr/telecharger/<jeton>`, sa validité (7 jours), la phrase
   « Si vous n'êtes pas à l'origine de cette demande, ignorez ce message », la
   signature mastermix.fr.
4. `GET /telecharger/<jeton>` :
   - jeton valide et non expiré : l'adresse est marquée confirmée (date de première
     confirmation conservée), puis une page « Merci » s'affiche avec le bouton de
     téléchargement `/telecharger/<jeton>/<fichier>`, la taille, l'empreinte SHA-256
     et la note SmartScreen (textes de la section Téléchargement du contenu) ;
   - jeton inconnu ou expiré : page « Lien expiré ou invalide » avec le formulaire
     pour en redemander un.
5. `GET /telecharger/<jeton>/<fichier>` : jeton valide, et `<fichier>` égal au
   fichier publié (`telechargement.fichier` du contenu) → le fichier est servi comme
   aujourd'hui (pièce jointe, plages `Range` acceptées). Le compteur de
   téléchargements est incrémenté une seule fois par requête complète (pas de
   `Range`, ou `Range` qui commence à 0), et la version téléchargée est notée.
   Sinon : 404.
6. Le lien reste réutilisable pendant 7 jours. Une nouvelle demande pour la même
   adresse remplace le jeton précédent (l'ancien lien cesse de fonctionner).

## 2. Garde-fous

- Adresse valide : forme `local@domaine.tld`, au plus 254 caractères, sans
  espace ni caractère de contrôle, mise en minuscules. Sinon, le formulaire
  réaffiche « Adresse e-mail invalide ».
- Limites :
  - 5 demandes par heure et par adresse IP (en mémoire seulement) ;
  - 3 e-mails par 24 h pour une même adresse (compté dans le fichier).
  Au-delà : « Trop de demandes, réessayez plus tard », aucun envoi.
- Jeton : 32 octets aléatoires (`secrets.token_urlsafe`). Seule son empreinte
  SHA-256 est stockée. Comparaison à temps constant.
- Les adresses jamais confirmées dont la demande a plus de 7 jours sont effacées
  (au fil des écritures du fichier).
- Échec d'envoi (Mailu injoignable, boîte non rattachée) : message « Envoi
  impossible pour le moment, réessayez dans quelques minutes » ; rien n'est
  enregistré pour cette demande.
- Les formulaires publics ne passent pas par l'API admin : pas de CSRF de
  session, mais le champ piège et les limites. Corps limité à 4 Ko.

## 3. Stockage

`data/telechargements.json` (jamais écrasé par `deploy.sh`, comme tout `data/`),
lu et écrit sous le verrou du `Store`, écriture atomique. Une entrée par adresse :

| Champ | Contenu |
|---|---|
| `email` | adresse en minuscules (clé) |
| `demande_le` | date de la première demande (ISO 8601) |
| `confirme_le` | date de la première confirmation, ou vide |
| `telechargements` | nombre de téléchargements complets |
| `version` | dernière version téléchargée (`2.18`) |
| `jeton_sha256` | empreinte du jeton en cours |
| `expire_le` | date d'expiration du jeton en cours |
| `envois` | dates des e-mails des dernières 24 h (pour la limite) |

Ni adresse IP, ni nom, ni navigateur. Le journal (`journal.log`) note « demande »,
« confirmation », « suppression », sans l'IP pour ces trois événements.

## 4. Backoffice

Nouvel onglet **Téléchargements** :
- compteurs : adresses confirmées, adresses en attente, téléchargements au total ;
- tableau trié par date de demande (la plus récente d'abord) : e-mail, confirmé
  le, demandé le, nombre de téléchargements, version ;
- bouton **Supprimer** par ligne (droit à l'effacement), avec confirmation ;
- bouton **Exporter en CSV** (`email;demande_le;confirme_le;telechargements;version`,
  UTF-8 avec BOM pour Excel) ;
- réglage **Adresse d'envoi** : une des boîtes rattachées, `contact@mastermix.fr`
  par défaut.

API admin (session et `X-CSRF` comme le reste) :
`GET /admin/api/telechargements`, `DELETE /admin/api/telechargements/<email>`,
`GET /admin/api/telechargements.csv`, `PUT /admin/api/reglages` (champ
`expediteur_telechargement`).

## 5. Mise en place

1. Créer `contact@mastermix.fr` sur Mailu :
   `docker exec mailu-admin-1 flask mailu user contact mastermix.fr '<mot de passe>'`
   (commande unitaire ; **jamais** `config-import`), mot de passe aléatoire de
   24 caractères, donné une seule fois à Ahmed.
2. Rattacher la boîte au site depuis le backoffice (bouton « Rattacher » de
   l'onglet Adresses) : mot de passe chiffré avec `data/.cle`.
3. Vérifier la délivrance : un e-mail de test vers une adresse Gmail (SPF, DKIM et
   DMARC de `mastermix.fr` déjà en place).

## 6. Ce qui ne change pas

- `/maj/mastermix2.json` et `/telechargements/<fichier>` restent publics (mise à
  jour automatique des 2.16 et suivantes). `SHA256SUMS.txt` reste public.
- Le contenu (`content.json`, `CONTENU_DEFAUT`) ne change pas de structure. Seul le
  gabarit change : les deux liens vers le fichier deviennent `#telechargement`, et
  la section reçoit le formulaire. `www/index.html` est régénéré et le test
  `test_render` le vérifie.

## Tests (unittest, faux SMTP existant)

- Parcours complet : demande → e-mail capturé contenant un lien → `GET` du lien →
  entrée confirmée → téléchargement du fichier → compteur à 1, version notée.
- Jeton inconnu, jeton expiré (horloge injectée), mauvais nom de fichier → 404 ou
  page « expiré ».
- Nouvelle demande : l'ancien lien ne fonctionne plus.
- Champ piège rempli : réponse identique, aucun e-mail, rien d'enregistré.
- Adresse invalide ; limite par IP (6e demande refusée) ; limite par adresse
  (4e e-mail en 24 h refusé).
- Échec d'envoi SMTP : message d'erreur, rien d'enregistré.
- Purge des demandes non confirmées de plus de 7 jours.
- Admin : liste, suppression, CSV (en-tête et BOM), refus sans session ou sans CSRF.
- Plage `Range: bytes=100-` : pas de double comptage.
- Le fichier brut `/telechargements/<fichier>` et le manifeste restent servis.
- `test_render` : `index.html` identique au rendu, aucun lien vers
  `telechargements/<fichier>.exe` dans la page.

## Hors périmètre

- Lettre d'information, envois groupés, désinscription.
- Page de politique de confidentialité complète (la phrase d'information suffit
  pour ce seul usage ; à ajouter si les usages s'étendent).
- Verrou strict du fichier brut.
- Captcha.
