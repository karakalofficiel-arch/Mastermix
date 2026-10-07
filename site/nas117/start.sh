#!/bin/sh
# Garde-fou nginx pour mastermix.fr sur le relais .117, sur le modele de
# karakalvision et karakal.media.
#
# TrueNAS regenere /etc/nginx/nginx.conf a chaque reboot ou modif reseau, ce qui
# efface la ligne « include /root/mastermix/nginx/mastermix.fr.conf; » : le
# domaine retombe alors sur l'interface TrueNAS (/ui/, certificat iXsystems).
# Incident du 2026-09-30 (reboot), constate le 2026-10-06.
#
# Ce script reinjecte l'include s'il a disparu, teste la configuration et
# recharge nginx, avec rollback si « nginx -t » echoue. Idempotent : execute au
# demarrage (Post-Init TrueNAS) et toutes les deux minutes (cron TrueNAS), sans
# effet de bord quand tout est en place. Deploye par site/deploy.sh 117.

APP=/root/mastermix
NGINX_CONF=/etc/nginx/nginx.conf
SITE_CONF=$APP/nginx/mastermix.fr.conf
LOG=$APP/start.log

[ -f "$NGINX_CONF" ] || exit 0
[ -f "$SITE_CONF" ] || exit 0
grep -q "mastermix.fr.conf" "$NGINX_CONF" && exit 0

echo "$(date) reinjection include nginx mastermix.fr" >> "$LOG"
cp "$NGINX_CONF" "$NGINX_CONF.mastermix.bak"
sed -i "\$i\\    include $SITE_CONF;" "$NGINX_CONF"
if nginx -t >/dev/null 2>&1; then
    nginx -s reload >/dev/null 2>&1
    echo "$(date) nginx recharge avec mastermix.fr" >> "$LOG"
else
    echo "$(date) ERREUR nginx -t : rollback" >> "$LOG"
    cp "$NGINX_CONF.mastermix.bak" "$NGINX_CONF"
fi
