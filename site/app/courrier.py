"""Courrier des boîtes @mastermix.fr : IMAP (lecture) et SMTP (envoi) vers Mailu.

Le serveur vit sur 192.168.1.166 ; on s'y connecte par l'adresse locale mais
le certificat est vérifié contre son vrai nom (mail.besancon.vip), comme dans
karakal.media. Les connexions IMAP/SMTP sont fabriquées par des fabriques
injectables pour les tests.
"""
import email
import email.policy
import email.utils
import html
import imaplib
import re
import smtplib
import socket
import ssl
import time
from email.header import decode_header, make_header
from email.message import EmailMessage
from html.parser import HTMLParser

DELAI = 12
LIMITE_LISTE = 60
LIMITE_CORPS = 200000
DOSSIERS = {"recus": "INBOX", "envoyes": "Sent"}
PIECES_MAX = 20 * 1024 * 1024

REGLAGES_DEFAUT = {
    "hote": "192.168.1.166",
    "nom_certificat": "mail.besancon.vip",
    "port_imap": 993,
    "port_smtp": 465,
}


class ErreurCourrier(Exception):
    """Panne explicable, montrée telle quelle à l'admin."""


# --- connexions ---------------------------------------------------------------
class _ImapLocal(imaplib.IMAP4_SSL):
    def __init__(self, adresse, nom_certificat, port, contexte):
        self._nom_certificat = nom_certificat
        super().__init__(adresse, port, ssl_context=contexte, timeout=DELAI)

    def _create_socket(self, timeout=None):
        brut = socket.create_connection((self.host, self.port), timeout or DELAI)
        return self.ssl_context.wrap_socket(brut, server_hostname=self._nom_certificat)


class _SmtpLocal(smtplib.SMTP_SSL):
    def __init__(self, adresse, nom_certificat, port, contexte):
        self._nom_certificat = nom_certificat
        super().__init__(adresse, port, timeout=DELAI, context=contexte)

    def _get_socket(self, host, port, timeout):
        brut = socket.create_connection((host, port), timeout)
        return self.context.wrap_socket(brut, server_hostname=self._nom_certificat)


def fabrique_imap(reglages):
    r = dict(REGLAGES_DEFAUT, **reglages)
    return _ImapLocal(r["hote"], r["nom_certificat"], int(r["port_imap"]), ssl.create_default_context())


def fabrique_smtp(reglages):
    r = dict(REGLAGES_DEFAUT, **reglages)
    return _SmtpLocal(r["hote"], r["nom_certificat"], int(r["port_smtp"]), ssl.create_default_context())


def _connexion_imap(reglages, email_, mot_de_passe, fabrique):
    try:
        client = fabrique(reglages)
        client.login(email_, mot_de_passe)
    except (OSError, ssl.SSLError) as erreur:
        raise ErreurCourrier("Serveur de courrier injoignable : %s" % erreur) from erreur
    except imaplib.IMAP4.error as erreur:
        raise ErreurCourrier("Connexion refusée : identifiants incorrects.") from erreur
    return client


def verifier_identifiants(reglages, email_, mot_de_passe, fabrique=fabrique_imap):
    client = _connexion_imap(reglages, email_, mot_de_passe, fabrique)
    try:
        client.logout()
    except (imaplib.IMAP4.error, OSError):
        pass
    return True


# --- décodage -------------------------------------------------------------------
def _texte(valeur):
    if not valeur:
        return ""
    try:
        return str(make_header(decode_header(valeur)))
    except (UnicodeDecodeError, ValueError, LookupError):
        return str(valeur)


def _date_iso(valeur):
    try:
        return email.utils.parsedate_to_datetime(valeur).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, IndexError):
        return ""


class _Assainisseur(HTMLParser):
    """Garde un sous-ensemble de balises ; supprime scripts, styles, images distantes."""
    AUTORISEES = {"p", "br", "b", "strong", "i", "em", "u", "a", "ul", "ol", "li", "blockquote",
                  "h1", "h2", "h3", "h4", "pre", "code", "table", "tr", "td", "th", "thead", "tbody", "div", "span", "hr"}
    IGNOREES = {"script", "style", "head", "title", "iframe", "object", "embed"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sortie = []
        self._ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNOREES:
            self._ignore += 1
            return
        if self._ignore or tag not in self.AUTORISEES:
            return
        if tag == "a":
            href = dict(attrs).get("href", "") or ""
            if re.match(r"^(https?://|mailto:)", href, re.I):
                self.sortie.append('<a href="%s" rel="noopener noreferrer" target="_blank">' % html.escape(href, quote=True))
                return
        self.sortie.append("<%s>" % tag)

    def handle_endtag(self, tag):
        if tag in self.IGNOREES:
            self._ignore = max(0, self._ignore - 1)
            return
        if self._ignore or tag not in self.AUTORISEES or tag in ("br", "hr"):
            return
        self.sortie.append("</%s>" % tag)

    def handle_data(self, data):
        if not self._ignore:
            self.sortie.append(html.escape(data))


def assainir_html(source):
    p = _Assainisseur()
    p.feed(source or "")
    p.close()
    return "".join(p.sortie)


def analyser_message(brut):
    """Décompose un message brut en dict : sujet, de, a, date, texte, html, pieces."""
    msg = email.message_from_bytes(brut, policy=email.policy.default)
    texte, html_ = "", ""
    pieces = []
    for indice, partie in enumerate(msg.walk()):
        if partie.get_content_maintype() == "multipart":
            continue
        disposition = partie.get_content_disposition()
        nom = partie.get_filename()
        if disposition == "attachment" or (nom and disposition != "inline") or (nom and partie.get_content_maintype() not in ("text",)):
            charge = partie.get_payload(decode=True) or b""
            pieces.append({"indice": indice, "nom": nom or "piece-%d" % indice, "type": partie.get_content_type(), "taille": len(charge)})
            continue
        if partie.get_content_type() == "text/plain" and not texte:
            texte = partie.get_content()
        elif partie.get_content_type() == "text/html" and not html_:
            html_ = partie.get_content()
    return {
        "sujet": _texte(msg.get("Subject", "")),
        "de": _texte(msg.get("From", "")),
        "a": _texte(msg.get("To", "")),
        "cc": _texte(msg.get("Cc", "")),
        "date": _date_iso(msg.get("Date", "")),
        "message_id": msg.get("Message-ID", ""),
        "references": msg.get("References", ""),
        "texte": texte[:LIMITE_CORPS],
        "html": assainir_html(html_[:LIMITE_CORPS]) if html_ else "",
        "pieces": pieces,
    }


def extraire_piece(brut, indice):
    msg = email.message_from_bytes(brut, policy=email.policy.default)
    for i, partie in enumerate(msg.walk()):
        if i == int(indice):
            return partie.get_filename() or "piece-%d" % i, partie.get_content_type(), partie.get_payload(decode=True) or b""
    raise ErreurCourrier("Pièce jointe introuvable.")


# --- lecture IMAP -----------------------------------------------------------------
class Boite:
    def __init__(self, reglages, email_, mot_de_passe, fabrique_imap_=fabrique_imap, fabrique_smtp_=fabrique_smtp):
        self.reglages = dict(REGLAGES_DEFAUT, **(reglages or {}))
        self.email = email_
        self.mot_de_passe = mot_de_passe
        self._fabrique_imap = fabrique_imap_
        self._fabrique_smtp = fabrique_smtp_

    def _imap(self, dossier):
        client = _connexion_imap(self.reglages, self.email, self.mot_de_passe, self._fabrique_imap)
        code, _ = client.select(DOSSIERS.get(dossier, "INBOX"))
        if code != "OK":
            if dossier == "envoyes":
                client.create("Sent")
                client.select("Sent")
            else:
                raise ErreurCourrier("Dossier introuvable.")
        return client

    def lister(self, dossier="recus"):
        client = self._imap(dossier)
        try:
            code, donnees = client.search(None, "ALL")
            uids = donnees[0].split() if code == "OK" and donnees and donnees[0] else []
            uids = uids[-LIMITE_LISTE:]
            resultat = []
            if uids:
                code, reponses = client.fetch(b",".join(uids), "(FLAGS RFC822.SIZE BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])")
                for reponse in reponses:
                    if not isinstance(reponse, tuple):
                        continue
                    entete, contenu = reponse
                    m = re.match(rb"(\d+) \(", entete)
                    if not m:
                        continue
                    msg = email.message_from_bytes(contenu, policy=email.policy.default)
                    drapeaux = entete.decode("latin-1")
                    resultat.append({
                        "id": m.group(1).decode(),
                        "de": _texte(msg.get("From", "")),
                        "a": _texte(msg.get("To", "")),
                        "sujet": _texte(msg.get("Subject", "")) or "(sans objet)",
                        "date": _date_iso(msg.get("Date", "")),
                        "lu": "\\Seen" in drapeaux,
                        "taille": int((re.search(r"RFC822.SIZE (\d+)", drapeaux) or [0, 0])[1]),
                    })
            resultat.reverse()
            return resultat
        finally:
            self._fermer(client)

    def lire(self, dossier, id_):
        client = self._imap(dossier)
        try:
            code, donnees = client.fetch(str(int(id_)), "(BODY.PEEK[])")
            if code != "OK" or not donnees or not isinstance(donnees[0], tuple):
                raise ErreurCourrier("Message introuvable.")
            brut = donnees[0][1]
            message = analyser_message(brut)
            message["id"] = str(int(id_))
            message["dossier"] = dossier
            return message, brut
        finally:
            self._fermer(client)

    def marquer(self, dossier, id_, lu):
        client = self._imap(dossier)
        try:
            client.store(str(int(id_)), "+FLAGS" if lu else "-FLAGS", "\\Seen")
        finally:
            self._fermer(client)

    def supprimer(self, dossier, id_):
        client = self._imap(dossier)
        try:
            client.store(str(int(id_)), "+FLAGS", "\\Deleted")
            client.expunge()
        finally:
            self._fermer(client)

    def _fermer(self, client):
        try:
            client.close()
        except (imaplib.IMAP4.error, OSError):
            pass
        try:
            client.logout()
        except (imaplib.IMAP4.error, OSError):
            pass

    # --- envoi SMTP --------------------------------------------------------
    def envoyer(self, nom, a, sujet, texte, cc=(), pieces=(), en_reponse_a=None, references=None):
        """Envoie un message et le copie dans Envoyés. pieces : [(nom, type, octets)]."""
        destinataires = _adresses(a)
        copies = _adresses(cc)
        if not destinataires:
            raise ErreurCourrier("Aucun destinataire valide.")
        if sum(len(p[2]) for p in pieces) > PIECES_MAX:
            raise ErreurCourrier("Pièces jointes : 20 Mo maximum au total.")
        msg = construire_message(self.email, nom, destinataires, copies, sujet, texte, pieces, en_reponse_a, references)
        try:
            client = self._fabrique_smtp(self.reglages)
            client.login(self.email, self.mot_de_passe)
            client.send_message(msg, from_addr=self.email, to_addrs=destinataires + copies)
            client.quit()
        except smtplib.SMTPAuthenticationError as erreur:
            raise ErreurCourrier("Envoi refusé : identifiants incorrects.") from erreur
        except (smtplib.SMTPException, OSError, ssl.SSLError) as erreur:
            raise ErreurCourrier("Envoi impossible : %s" % erreur) from erreur
        self._copier_envoye(msg)
        return msg["Message-ID"]

    def _copier_envoye(self, msg):
        try:
            client = self._imap("envoyes")
        except ErreurCourrier:
            return
        try:
            client.append("Sent", "\\Seen", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        except (imaplib.IMAP4.error, OSError):
            pass
        finally:
            self._fermer(client)


def _adresses(valeur):
    if isinstance(valeur, str):
        valeur = re.split(r"[,;\s]+", valeur)
    resultat = []
    for v in valeur or ():
        v = (v or "").strip()
        if v and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            resultat.append(v)
    return resultat


def construire_message(expediteur, nom, a, cc, sujet, texte, pieces=(), en_reponse_a=None, references=None):
    msg = EmailMessage()
    msg["From"] = email.utils.formataddr((nom or "", expediteur))
    msg["To"] = ", ".join(a)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = sujet or "(sans objet)"
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=expediteur.split("@", 1)[1])
    if en_reponse_a:
        msg["In-Reply-To"] = en_reponse_a
        msg["References"] = ((references or "") + " " + en_reponse_a).strip()
    msg.set_content(texte or "")
    for nom_piece, type_mime, octets in pieces:
        maintype, _, subtype = (type_mime or "application/octet-stream").partition("/")
        msg.add_attachment(octets, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=nom_piece)
    return msg


def citer(message):
    """Texte cité pour une réponse."""
    lignes = (message.get("texte") or "").splitlines()
    return "\n\nLe %s, %s a écrit :\n%s" % (message.get("date", ""), message.get("de", ""), "\n".join("> " + l for l in lignes))
