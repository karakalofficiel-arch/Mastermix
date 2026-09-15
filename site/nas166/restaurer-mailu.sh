#!/bin/bash
# Restauration des domaines et comptes Mailu effacés le 2026-09-15 par un
# `config-import` lancé sans `-u` (mode remplacement). Les boîtes (courriers) et
# la clé DKIM de besancon.vip sont intactes sur disque ; seuls les enregistrements
# de la base (domaines, comptes, mots de passe hachés) sont recréés ici.
#
# À lancer depuis le poste de travail :   bash site/nas166/restaurer-mailu.sh
#
# Mots de passe :
#   admin@besancon.vip      -> "Doudia101877+" (mot de passe boîte/SMTP documenté ; devient aussi
#                              celui de l'interface admin Mailu, l'ancien ednURrd1y86M7r est perdu)
#   agent@besancon.vip      -> "Bes2026Agent!kR9" (documenté)
#   matune@karalook.org     -> repris tel quel des réglages de karakal.media sur .117 (jamais affiché)
#   test@, gestion@, inscription-test@besancon.vip -> générés et AFFICHÉS en fin de script
set -euo pipefail
KEY117="A:/claude/truenas/.ssh/id_ed25519"

echo "== mot de passe de matune@karalook.org (lu sur .117, non affiché)"
P_MATUNE="$(ssh -o ConnectTimeout=10 -i "$KEY117" root@192.168.1.117 'python3 -c "import json; print(json.load(open(\"/root/karakalmedia/data/settings.json\"))[\"imap_password\"])"')"
[ -n "$P_MATUNE" ] || { echo "introuvable : arrêt"; exit 1; }

gen() { python -c "import secrets,string; a=string.ascii_letters+string.digits; print(''.join(secrets.choice(a) for _ in range(16)))"; }
P_TEST=$(gen); P_GESTION=$(gen); P_INSCR=$(gen)

printf '%s\n%s\n%s\n%s\n' "$P_MATUNE" "$P_TEST" "$P_GESTION" "$P_INSCR" | ssh -o ConnectTimeout=20 karakal166 '
read PM; read PT; read PG; read PI
cd /mnt/karakalia/mailu
M() { sudo docker compose exec -T admin flask mailu "$@"; }
echo "== domaines"
M domain besancon.vip 2>&1 | tail -1
M domain karalook.org 2>&1 | tail -1
echo "== administrateur global"
M admin admin besancon.vip "Doudia101877+" 2>&1 | tail -1
echo "== comptes"
M user agent besancon.vip "Bes2026Agent!kR9" 2>&1 | tail -1
M user test besancon.vip "$PT" 2>&1 | tail -1
M user gestion besancon.vip "$PG" 2>&1 | tail -1
M user inscription-test besancon.vip "$PI" 2>&1 | tail -1
M user matune karalook.org "$PM" 2>&1 | tail -1
echo "== état de la base"
M config-export --dns domain user 2>/dev/null | grep -E "^  - name:|email:|global_admin|dns_dkim" | sed -E "s/(p=[A-Za-z0-9+\/]{24}).*/\1…/"
echo "== connexions IMAP"
for cred in "admin@besancon.vip:Doudia101877+" "agent@besancon.vip:Bes2026Agent!kR9" "matune@karalook.org:$PM" "test@besancon.vip:$PT" "gestion@besancon.vip:$PG" "inscription-test@besancon.vip:$PI"; do
  u=${cred%%:*}
  r=$(curl -s -m 10 -k --url "imaps://192.168.1.166:993/INBOX" --user "$cred" -X "STATUS INBOX (MESSAGES)" 2>&1 | tr -d "\r" | grep -oE "MESSAGES [0-9]+")
  echo "$u -> ${r:-ECHEC}"
done
echo "== .env de l application besancon.vip (SMTP_PASS doit valoir Doudia101877+ ; sinon : sudo sed -i s/^SMTP_PASS=.*/SMTP_PASS=Doudia101877+/ /mnt/karakalia/besancon-vip/.env puis docker compose restart api)"
sudo grep -cE "^SMTP_PASS=Doudia101877\+$" /mnt/karakalia/besancon-vip/.env | sed "s/^1$/SMTP_PASS conforme à la doc/;s/^0$/SMTP_PASS DIFFERENT de la doc (bug + en trop ?) : à corriger dans .env/"
sudo grep -cE "^AGENT_SMTP_PASS=Bes2026Agent!kR9$" /mnt/karakalia/besancon-vip/.env | sed "s/^1$/AGENT_SMTP_PASS conforme/;s/^0$/AGENT_SMTP_PASS DIFFERENT : à corriger dans .env/"
echo "== jeton API Mailu (à coller dans mastermix.fr/admin > Réglages)"
sudo grep "^API_TOKEN=" mailu.env | cut -d= -f2
'
echo
echo "== Mots de passe générés (à conserver, ils ne seront plus affichés) :"
echo "test@besancon.vip              $P_TEST"
echo "gestion@besancon.vip           $P_GESTION"
echo "inscription-test@besancon.vip  $P_INSCR"
