#!/bin/sh
# Émet le certificat Let's Encrypt de mastermix.fr et l'installe pour nginx.
#
# À lancer UNE FOIS, après que mastermix.fr et www.mastermix.fr pointent sur
# l'IP publique de la Freebox (vérification HTTP-01 sur le port 80, qui arrive
# sur ce serveur). Le renouvellement est ensuite automatique : acme.sh --cron
# tourne déjà tous les jours à 10h35 (crontab root).
#
#     /root/mastermix/certs/issue-letsencrypt.sh
#
# Tant que ce script n'a pas été lancé, le vhost utilise un certificat
# auto-signé de substitution (généré par deploy.sh) pour que nginx démarre.

set -e
ACME=/root/karakalvision/acme/acme.sh
CERTS=/root/mastermix/certs

mkdir -p /var/www/acme "$CERTS"

# --server letsencrypt : acme.sh v3 vise ZeroSSL par défaut, qui exige un compte.
"$ACME" --issue --home /root/.acme.sh --server letsencrypt \
    -d mastermix.fr -d www.mastermix.fr \
    -w /var/www/acme --keylength ec-256

"$ACME" --install-cert --home /root/.acme.sh -d mastermix.fr --ecc \
    --key-file       "$CERTS/mastermix.fr.key.pem" \
    --fullchain-file "$CERTS/mastermix.fr.fullchain.pem" \
    --reloadcmd      "nginx -t && nginx -s reload"

chmod 600 "$CERTS/mastermix.fr.key.pem"
echo "Certificat installé. Vérification :"
openssl x509 -in "$CERTS/mastermix.fr.fullchain.pem" -noout -subject -issuer -dates
