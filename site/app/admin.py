"""Compte administrateur unique, sessions, blocage après échecs, jeton CSRF.

Mot de passe haché pbkdf2-sha256 (200 000 itérations, sel 16 octets) dans
data/admin.json. Une seule session active, expirée après 12 h d'inactivité.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from pathlib import Path

ITERATIONS = 200_000
SESSION_DUREE = 12 * 3600
ECHECS_MAX = 5
ECHECS_FENETRE = 15 * 60
BLOCAGE_DUREE = 15 * 60
MOT_DE_PASSE_MIN = 12
ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generer_mot_de_passe(longueur=16):
    return "".join(secrets.choice(ALPHABET) for _ in range(longueur))


def hacher(mot_de_passe, sel=None, iterations=ITERATIONS):
    sel = sel or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), bytes.fromhex(sel), iterations)
    return {"algo": "pbkdf2-sha256", "sel": sel, "iterations": iterations, "hash": dk.hex()}


def verifier(mot_de_passe, enregistrement):
    try:
        dk = hashlib.pbkdf2_hmac(
            "sha256", mot_de_passe.encode("utf-8"),
            bytes.fromhex(enregistrement["sel"]), int(enregistrement["iterations"]),
        )
        return hmac.compare_digest(dk.hex(), enregistrement["hash"])
    except (KeyError, ValueError, TypeError):
        return False


class Admin:
    def __init__(self, data_dir, horloge=time.time):
        self.chemin = Path(data_dir) / "admin.json"
        self.horloge = horloge
        self._verrou = threading.Lock()
        self._session = None          # {"jeton", "csrf", "vu"}
        self._echecs = {}             # ip -> [horodatages]
        self._blocages = {}           # ip -> fin du blocage
        self.mot_de_passe_initial = None
        if not self.chemin.exists():
            self.mot_de_passe_initial = generer_mot_de_passe()
            self._ecrire(hacher(self.mot_de_passe_initial))

    def _ecrire(self, enregistrement):
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.chemin.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(enregistrement, f)
        if os.name != "nt":
            os.chmod(tmp, 0o600)
        os.replace(tmp, self.chemin)

    def _lire(self):
        with open(self.chemin, encoding="utf-8") as f:
            return json.load(f)

    # --- blocage -----------------------------------------------------------
    def bloque(self, ip):
        fin = self._blocages.get(ip)
        if fin and fin > self.horloge():
            return True
        self._blocages.pop(ip, None)
        return False

    def _noter_echec(self, ip):
        maintenant = self.horloge()
        recents = [t for t in self._echecs.get(ip, []) if maintenant - t < ECHECS_FENETRE]
        recents.append(maintenant)
        self._echecs[ip] = recents
        if len(recents) >= ECHECS_MAX:
            self._blocages[ip] = maintenant + BLOCAGE_DUREE
            self._echecs[ip] = []

    # --- connexion ---------------------------------------------------------
    def connecter(self, mot_de_passe, ip):
        """Renvoie (jeton_session, jeton_csrf) ou None. Lève PermissionError si bloqué."""
        with self._verrou:
            if self.bloque(ip):
                raise PermissionError("trop d'échecs, réessayez plus tard")
            if not verifier(mot_de_passe or "", self._lire()):
                self._noter_echec(ip)
                return None
            self._echecs.pop(ip, None)
            self._session = {"jeton": secrets.token_urlsafe(32), "csrf": secrets.token_urlsafe(32), "vu": self.horloge()}
            return self._session["jeton"], self._session["csrf"]

    def session_valide(self, jeton):
        """Renvoie le jeton CSRF si la session est valide (et la prolonge), sinon None."""
        with self._verrou:
            s = self._session
            if not s or not jeton or not hmac.compare_digest(s["jeton"], jeton):
                return None
            if self.horloge() - s["vu"] > SESSION_DUREE:
                self._session = None
                return None
            s["vu"] = self.horloge()
            return s["csrf"]

    def csrf_valide(self, jeton, csrf):
        attendu = self.session_valide(jeton)
        return bool(attendu and csrf and hmac.compare_digest(attendu, csrf))

    def deconnecter(self):
        with self._verrou:
            self._session = None

    def changer_mot_de_passe(self, ancien, nouveau):
        if len(nouveau or "") < MOT_DE_PASSE_MIN:
            raise ValueError("%d caractères minimum" % MOT_DE_PASSE_MIN)
        with self._verrou:
            if not verifier(ancien or "", self._lire()):
                raise ValueError("ancien mot de passe incorrect")
            self._ecrire(hacher(nouveau))
            self.mot_de_passe_initial = None
