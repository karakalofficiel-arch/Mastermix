# Site mastermix.fr

Page de présentation, backoffice de contenu et courrier des boîtes `@mastermix.fr`.
Serveur Python autonome (bibliothèque standard), spec : `docs/superpowers/specs/2026-09-15-mastermix-site-admin-courrier-design.md`.

## Architecture

```
Internet ── Freebox (80/443 → 192.168.1.117) ── nginx .117 (TLS, vhost mastermix.fr)
                                                     │ proxy_pass
                                              192.168.1.166:8095 ── conteneur mastermix-site (python:3.12-alpine)
                                                                     /mnt/karakalia/mastermix-site/{app,data,www}
                                                                             │ IMAP 993 / SMTP 465 / API 8443
                                                                     Mailu (.166) : domaine mastermix.fr
```

| Élément | Emplacement |
|---|---|
| Code | `site/app/` (`server.py`, `render.py`, `gabarit.html`, `markdown_lite.py`, `store.py`, `admin.py`, `admin_ui.py`, `secrets_box.py`, `mailu_api.py`, `courrier.py`, `tests/`) |
| Page publique de référence | `site/www/index.html` (le rendu de `CONTENU_DEFAUT` doit lui être identique : test `test_render`) |
| Conteneur .166 | `/mnt/karakalia/mastermix-site/` : `app/` (lecture seule), `data/` (contenu, pages, réglages, journal, sauvegardes, clé), `www/` (logo, captures, `media/`, `telechargements/`) — port `192.168.1.166:8095` |
| Vhost .117 | `/root/mastermix/nginx/mastermix.fr.conf`, inclus par une ligne dans `/etc/nginx/nginx.conf` |
| Certificat .117 | `/root/mastermix/certs/` (Let's Encrypt via acme.sh, renouvellement cron 10h35) |
| Rollback statique | `docker-compose.nginx.yml` dans le dossier du conteneur |

## Backoffice

- URL : https://mastermix.fr/admin — un seul compte. Mot de passe initial affiché une fois dans `docker logs mastermix-site` (ligne `MOT DE PASSE ADMIN INITIAL`), à changer dans Réglages.
- Onglets : Contenu (sections de l'accueil), Pages (Markdown simplifié, URL `/p/<slug>`), Fichiers (images `media/` 8 Mo, installeurs `telechargements/` 200 Mo, SHA-256 calculé), Courrier, Adresses, Réglages (mot de passe, API Mailu, sauvegardes, journal).
- Sécurité : cookie `mm_session` (HttpOnly, Secure, SameSite=Strict, 12 h), en-tête `X-CSRF` sur chaque écriture, 5 échecs / 15 min par IP = blocage 15 min, journal `data/journal.log`.
- Secrets : `data/settings.json` (mode 600) ; mots de passe de boîtes et jeton Mailu chiffrés avec `data/.cle`. Quiconque a le volume complet a les deux : ne pas copier `data/` hors du serveur sans précaution.

## Courrier

- Serveur : Mailu sur .166, domaine `mastermix.fr` (créé le 2026-09-15, DKIM sélecteur `dkim`).
- API Mailu : `API=true` + `API_TOKEN` dans `/mnt/karakalia/mailu/mailu.env`. URL à saisir dans Réglages : `https://mail.besancon.vip:8443/api/v1` (le serveur se connecte à l'IP `hote` = 192.168.1.166 et vérifie le certificat contre `mail.besancon.vip`).
- Adresses : création via l'API ; le mot de passe est conservé chiffré pour ouvrir la boîte dans Courrier. Réinitialisation possible. Une boîte créée ailleurs se rattache avec son mot de passe.
- Lecture IMAP `192.168.1.166:993`, envoi SMTPS `192.168.1.166:465`, copie dans `Sent`.
- Webmail Roundcube pour les personnes : https://mail.besancon.vip/webmail

## DNS mastermix.fr (IONOS)

| Type | Nom | Valeur |
|---|---|---|
| A | `@`, `www` | `82.66.209.160` |
| MX | `@` | `10 mail.besancon.vip` |
| TXT | `@` | `v=spf1 ip4:82.66.209.160 -all` |
| TXT | `dkim._domainkey` | clé Mailu (`flask mailu config-export --dns domain`) |
| TXT | `_dmarc` | `v=DMARC1; p=quarantine; rua=mailto:postmaster@mastermix.fr` |

## Déployer

```bash
bash site/deploy.sh 166   # tests, puis app/ + www de base + composes → .166, recréation du conteneur
bash site/deploy.sh 117   # vhost + certificat provisoire + include nginx (idempotent)
```

Jamais écrasés sur .166 : `data/`, `www/media/`, `www/telechargements/`. Tests : `cd site && python -m unittest discover -s app/tests -t .` (72 tests).

## Piège Mailu (incident du 2026-09-15)

`flask mailu config-import` **sans `-u`** remplace toute la configuration : domaines, comptes et alias absents du YAML sont supprimés. Toujours `-u` (mode fusion), ou les commandes unitaires `flask mailu domain|user|alias|admin`. Restauration : `site/nas166/restaurer-mailu.sh`.

## Rollback

- Site : `cd /mnt/karakalia/mastermix-site && sudo docker compose down && sudo docker compose -f docker-compose.nginx.yml up -d`.
- Relais : retirer la ligne `include /root/mastermix/nginx/mastermix.fr.conf;` de `/etc/nginx/nginx.conf` sur .117, `nginx -t && nginx -s reload`.
