#!/bin/bash
# Déploie le site mastermix.fr :
#   1. .166 (karakal166) : application Python (site + admin + courrier) sur 192.168.1.166:8095
#   2. .117 (relais public) : vhost mastermix.fr + certificat (auto-signé tant que
#      issue-letsencrypt.sh n'a pas été lancé) + include dans nginx.conf
# Idempotent : relançable après toute modification de site/.
#
#   bash site/deploy.sh            # tout
#   bash site/deploy.sh 166        # seulement l'application sur .166
#   bash site/deploy.sh 117        # seulement le relais sur .117
#
# Ce qui n'est jamais écrasé sur .166 : data/ (contenu, pages, réglages, journal,
# sauvegardes, clé des secrets), www/media/ et www/telechargements/ (fichiers
# déposés depuis l'admin). Les installeurs présents dans site/www/telechargements/
# en local sont envoyés s'ils manquent sur le serveur.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
KEY117="A:/claude/truenas/.ssh/id_ed25519"
SSH117="ssh -o ConnectTimeout=10 -i $KEY117 root@192.168.1.117"
DEST=/mnt/karakalia/mastermix-site
WHAT="${1:-all}"

if [ "$WHAT" = all ] || [ "$WHAT" = 166 ]; then
  echo "== .166 : application"
  ( cd "$HERE" && python -m unittest discover -s app/tests -t . 2>&1 | tail -1 | grep -q "^OK" ) || { echo "TESTS EN ÉCHEC, déploiement annulé"; exit 1; }
  ssh karakal166 "sudo mkdir -p $DEST/data $DEST/www/media $DEST/www/telechargements"
  # code (app/ sans tests ni caches), fichiers publics de base, composes, nginx.conf de secours
  tar czf - -C "$HERE" --exclude='__pycache__' --exclude='app/tests' \
      app www/index.html www/logo.svg www/editeur.jpg www/mixer.jpg \
      -C "$HERE/nas166" docker-compose.yml docker-compose.nginx.yml nginx.conf \
    | ssh karakal166 "sudo tar xzf - -C $DEST --overwrite"
  # installeurs : uniquement ceux qui manquent côté serveur
  for f in "$HERE"/www/telechargements/*.exe "$HERE"/www/telechargements/*.zip; do
    [ -f "$f" ] || continue
    nom="$(basename "$f")"
    if ! ssh karakal166 "test -f $DEST/www/telechargements/'$nom'"; then
      echo "   envoi de $nom"
      ssh karakal166 "sudo tee $DEST/www/telechargements/'$nom' > /dev/null" < "$f"
    fi
  done
  ssh karakal166 "sudo chown -R 1000:1000 $DEST/data $DEST/www && sudo chmod 700 $DEST/data"
  # --force-recreate : le code est monté en lecture seule, un simple "up" ne le relirait pas.
  ssh karakal166 "cd $DEST && sudo docker compose up -d --force-recreate"
  sleep 3
  echo -n "healthz .166:8095 -> "; curl -s -m 5 http://192.168.1.166:8095/healthz
  ssh karakal166 "sudo docker logs mastermix-site 2>&1 | grep -E 'MOT DE PASSE ADMIN INITIAL|Traceback|Error' | tail -3" || true
fi

if [ "$WHAT" = all ] || [ "$WHAT" = 117 ]; then
  echo "== .117 : vhost + certificat"
  $SSH117 'mkdir -p /root/mastermix/nginx /root/mastermix/certs /var/www/acme'
  scp -q -i "$KEY117" "$HERE/nas117/mastermix.fr.conf" root@192.168.1.117:/root/mastermix/nginx/mastermix.fr.conf
  scp -q -i "$KEY117" "$HERE/nas117/issue-letsencrypt.sh" root@192.168.1.117:/root/mastermix/certs/issue-letsencrypt.sh
  $SSH117 '
set -e
chmod +x /root/mastermix/certs/issue-letsencrypt.sh
C=/root/mastermix/certs
# Certificat de substitution (auto-signé) pour que nginx accepte le vhost avant Let'"'"'s Encrypt.
if [ ! -s $C/mastermix.fr.fullchain.pem ]; then
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 30 \
    -subj "/CN=mastermix.fr" -addext "subjectAltName=DNS:mastermix.fr,DNS:www.mastermix.fr" \
    -keyout $C/mastermix.fr.key.pem -out $C/mastermix.fr.fullchain.pem 2>/dev/null
  chmod 600 $C/mastermix.fr.key.pem
  echo "certificat auto-signé de substitution créé"
fi
# Include dans nginx.conf : une ligne ajoutée juste après celle de karakal.media, rien d'"'"'autre n'"'"'est modifié.
if ! grep -q "/root/mastermix/nginx/mastermix.fr.conf" /etc/nginx/nginx.conf; then
  cp -a /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak-mastermix-$(date +%Y%m%d-%H%M)
  sed -i "\|include /root/karakalmedia/nginx/karakal.media.conf;|a\\    include /root/mastermix/nginx/mastermix.fr.conf;" /etc/nginx/nginx.conf
  echo "include ajouté dans nginx.conf"
fi
nginx -t && nginx -s reload
echo "nginx rechargé"
'
  echo -n "relais .117 (SNI mastermix.fr) -> "
  curl -sk -m 8 --resolve mastermix.fr:443:192.168.1.117 -o /dev/null -w "%{http_code}\n" https://mastermix.fr/
fi
