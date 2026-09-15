"""Client de l'API REST Mailu (v1) : boîtes, alias, mots de passe.

Bibliothèque standard uniquement (http.client). Le serveur Mailu vit sur le
réseau local mais son certificat porte son nom public (mail.besancon.vip) : on
se connecte à l'adresse locale (`adresse`) et on vérifie le certificat contre
le nom d'hôte de l'URL. Jamais de journalisation du jeton ni des mots de passe.
"""
import http.client
import json
import re
import socket
import ssl
import urllib.parse

DELAI = 15
_LOCAL = re.compile(r"^[a-z0-9._-]{1,64}$")


class ErreurMailu(Exception):
    """Panne ou refus de l'API, à afficher tel quel à l'admin."""


def valider_partie_locale(local):
    return bool(_LOCAL.match(local or ""))


class _HTTPSLocal(http.client.HTTPSConnection):
    """HTTPS vers une adresse IP, certificat vérifié contre un autre nom."""

    def __init__(self, adresse, port, nom_certificat, contexte):
        super().__init__(adresse, port, timeout=DELAI, context=contexte)
        self._nom_certificat = nom_certificat

    def connect(self):
        brut = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = self._context.wrap_socket(brut, server_hostname=self._nom_certificat)


class MailuAPI:
    def __init__(self, base_url, jeton, domaine, adresse=None):
        u = urllib.parse.urlsplit(base_url.rstrip("/"))
        if u.scheme not in ("http", "https") or not u.hostname:
            raise ErreurMailu("URL de l'API Mailu invalide.")
        self.schema = u.scheme
        self.hote = u.hostname
        self.port = u.port or (443 if u.scheme == "https" else 80)
        self.prefixe = u.path.rstrip("/")
        self.adresse = adresse or self.hote
        self.jeton = jeton
        self.domaine = domaine

    def _connexion(self):
        if self.schema == "https":
            return _HTTPSLocal(self.adresse, self.port, self.hote, ssl.create_default_context())
        return http.client.HTTPConnection(self.adresse, self.port, timeout=DELAI)

    # --- transport ---------------------------------------------------------
    def _appel(self, methode, chemin, corps=None):
        entetes = {"Authorization": "Bearer " + self.jeton, "Accept": "application/json", "Host": self.hote}
        donnees = None
        if corps is not None:
            donnees = json.dumps(corps).encode("utf-8")
            entetes["Content-Type"] = "application/json"
        try:
            c = self._connexion()
            c.request(methode, self.prefixe + chemin, body=donnees, headers=entetes)
            reponse = c.getresponse()
            code, brut = reponse.status, reponse.read()
            c.close()
        except (OSError, ssl.SSLError, http.client.HTTPException) as erreur:
            raise ErreurMailu("API Mailu injoignable : %s" % erreur)
        if code >= 400:
            detail = ""
            try:
                detail = json.loads(brut.decode("utf-8")).get("message", "")
            except (ValueError, AttributeError):
                pass
            if code == 401:
                raise ErreurMailu("API Mailu : jeton refusé (401).")
            if code == 404:
                raise ErreurMailu("API Mailu : introuvable (%s)." % (detail or chemin))
            if code == 409:
                raise ErreurMailu("API Mailu : existe déjà (%s)." % (detail or chemin))
            raise ErreurMailu("API Mailu : erreur %d %s" % (code, detail))
        if not brut:
            return None
        try:
            return json.loads(brut.decode("utf-8"))
        except ValueError:
            raise ErreurMailu("API Mailu : réponse illisible.")

    def _adresse(self, local):
        if not valider_partie_locale(local):
            raise ErreurMailu("Adresse invalide : lettres minuscules, chiffres, . _ - (64 max).")
        return "%s@%s" % (local, self.domaine)

    # --- domaine -------------------------------------------------------------
    def verifier(self):
        """Renvoie le domaine tel que Mailu le connaît ; lève ErreurMailu sinon."""
        return self._appel("GET", "/domain/" + self.domaine)

    # --- boîtes --------------------------------------------------------------
    def lister_boites(self):
        boites = self._appel("GET", "/user") or []
        suffixe = "@" + self.domaine
        resultat = []
        for b in boites:
            email = b.get("email", "")
            if not email.endswith(suffixe):
                continue
            resultat.append({
                "email": email,
                "nom": b.get("displayed_name", "") or "",
                "quota": int(b.get("quota_bytes", 0) or 0),
                "utilise": int(b.get("quota_bytes_used", 0) or 0),
                "actif": bool(b.get("enabled", True)),
            })
        return sorted(resultat, key=lambda b: b["email"])

    def creer_boite(self, local, mot_de_passe, nom="", quota=1024 * 1024 * 1024):
        email = self._adresse(local)
        self._appel("POST", "/user", {
            "email": email, "raw_password": mot_de_passe, "displayed_name": nom or local,
            "quota_bytes": int(quota), "enabled": True, "enable_imap": True, "enable_pop": False,
        })
        return email

    def changer_mot_de_passe(self, email, mot_de_passe):
        self._appel("PATCH", "/user/" + urllib.parse.quote(email), {"raw_password": mot_de_passe})

    def supprimer_boite(self, email):
        self._appel("DELETE", "/user/" + urllib.parse.quote(email))

    # --- alias ---------------------------------------------------------------
    def lister_alias(self):
        alias = self._appel("GET", "/alias") or []
        suffixe = "@" + self.domaine
        resultat = [
            {"email": a.get("email", ""), "destinations": list(a.get("destination", []) or [])}
            for a in alias if a.get("email", "").endswith(suffixe)
        ]
        return sorted(resultat, key=lambda a: a["email"])

    def creer_alias(self, local, destinations):
        email = self._adresse(local)
        destinations = [d.strip() for d in destinations if d.strip()]
        if not destinations:
            raise ErreurMailu("Un alias a besoin d'au moins une destination.")
        self._appel("POST", "/alias", {"email": email, "destination": destinations, "comment": "", "wildcard": False})
        return email

    def supprimer_alias(self, email):
        self._appel("DELETE", "/alias/" + urllib.parse.quote(email))
