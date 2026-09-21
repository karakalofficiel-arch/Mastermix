#!/usr/bin/env python3
"""Serveur de mastermix.fr.

Écoute derrière le nginx de .117 qui termine TLS. Rend la page publique et les
pages libres depuis data/, sert www/, expose le backoffice /admin et son API JSON.
Bibliothèque standard uniquement.

    python3 server.py                    # 127.0.0.1:8095
    MM_HOST=0.0.0.0 MM_DATA=/data MM_WWW=/www python3 server.py
"""
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import sys
import threading
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import admin as admin_mod          # noqa: E402
from app import admin_ui, courrier, mailu_api, render, secrets_box, store as store_mod  # noqa: E402

HOST = os.environ.get("MM_HOST", "127.0.0.1")
PORT = int(os.environ.get("MM_PORT", "8095"))
SITE_URL = os.environ.get("MM_SITE_URL", "https://mastermix.fr")
DEV = os.environ.get("MM_DEV") == "1"
DOMAINE = os.environ.get("MM_DOMAINE", "mastermix.fr")
COOKIE_FLAGS = "HttpOnly; SameSite=Strict; Path=/admin" + ("" if DEV else "; Secure")
MAX_CORPS = 512 * 1024
MAX_MORCEAU = 1024 * 1024 + 1024
MAX_ENVOI = 30 * 1024 * 1024        # JSON avec pièces jointes en base64 (20 Mo bruts)
LIMITES = {"media": 8 * 1024 * 1024, "telechargements": 200 * 1024 * 1024}
EXTENSIONS = {"media": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}, "telechargements": {".exe", ".zip", ".msi"}}
_SVG_DANGER = re.compile(rb"<script|on[a-z]+\s*=|javascript:|<foreignObject|<iframe", re.I)

FABRIQUES = {"imap": courrier.fabrique_imap, "smtp": courrier.fabrique_smtp, "adresse_mailu": None}


class Application:
    """État partagé : store, compte admin, clé des secrets, téléversements en cours."""

    def __init__(self, data_dir, www_dir):
        self.store = store_mod.Store(data_dir, www_dir, contenu_defaut=render.CONTENU_DEFAUT)
        self.admin = admin_mod.Admin(data_dir)
        self.cle = secrets_box.charger_cle(data_dir)
        self.www = Path(www_dir)
        self.televersements = {}
        self._verrou = threading.Lock()
        if self.admin.mot_de_passe_initial:
            print("MOT DE PASSE ADMIN INITIAL : %s   (à changer dans Réglages)" % self.admin.mot_de_passe_initial, flush=True)
        self.store.lire_contenu()

    # --- réglages courrier -------------------------------------------------
    def reglages_courrier(self):
        r = self.store.lire_reglages()
        return {"hote": r.get("hote") or courrier.REGLAGES_DEFAUT["hote"],
                "nom_certificat": r.get("nom_certificat") or courrier.REGLAGES_DEFAUT["nom_certificat"]}

    def mailu(self):
        r = self.store.lire_reglages()
        if not r.get("mailu_url") or not r.get("mailu_jeton"):
            raise mailu_api.ErreurMailu("API Mailu non configurée : URL et jeton dans Réglages.")
        jeton = secrets_box.dechiffrer(self.cle, r["mailu_jeton"])
        # Connexion à l'adresse locale du serveur de courrier, certificat vérifié
        # contre le nom d'hôte de l'URL (mail.besancon.vip).
        return mailu_api.MailuAPI(r["mailu_url"], jeton, DOMAINE, adresse=FABRIQUES["adresse_mailu"] or self.reglages_courrier()["hote"])

    def boites_connues(self):
        return self.store.lire_reglages().get("boites", {})

    def enregistrer_boite(self, email, mot_de_passe, nom=""):
        with self._verrou:
            r = self.store.lire_reglages()
            boites = r.setdefault("boites", {})
            boites[email] = {"mdp": secrets_box.chiffrer(self.cle, mot_de_passe), "nom": nom or boites.get(email, {}).get("nom", "")}
            self.store.ecrire_reglages(r)

    def oublier_boite(self, email):
        with self._verrou:
            r = self.store.lire_reglages()
            if r.get("boites", {}).pop(email, None) is not None:
                self.store.ecrire_reglages(r)

    def boite(self, email):
        info = self.boites_connues().get(email)
        if not info:
            raise courrier.ErreurCourrier("Boîte non rattachée : mot de passe inconnu de l'admin.")
        mdp = secrets_box.dechiffrer(self.cle, info["mdp"])
        return courrier.Boite(self.reglages_courrier(), email, mdp, fabrique_imap_=FABRIQUES["imap"], fabrique_smtp_=FABRIQUES["smtp"]), info


APP = None


class Handler(BaseHTTPRequestHandler):
    server_version = "MasterMix/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if DEV:
            super().log_message(fmt, *args)

    # --- utilitaires -------------------------------------------------------
    @property
    def ip(self):
        return self.headers.get("X-Real-IP") or self.client_address[0]

    def cookies(self):
        c = SimpleCookie()
        c.load(self.headers.get("Cookie", ""))
        return {k: m.value for k, m in c.items()}

    def envoyer(self, code, corps=b"", type_="text/html; charset=utf-8", entetes=()):
        if isinstance(corps, str):
            corps = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in entetes:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corps)

    def json_(self, obj, code=200, entetes=()):
        self.envoyer(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", entetes)

    def erreur(self, code, message):
        if self.path.startswith("/admin/api/"):
            self.json_({"erreur": message}, code)
        else:
            self.envoyer(code, "<!DOCTYPE html><meta charset=utf-8><title>%d</title><p style='font-family:system-ui;padding:40px'>%s</p>" % (code, render.e(message)))

    def lire_corps(self, maximum=MAX_CORPS):
        longueur = int(self.headers.get("Content-Length") or 0)
        if longueur > maximum:
            raise ValueError("corps trop volumineux")
        return self.rfile.read(longueur) if longueur else b""

    def lire_json(self, maximum=MAX_CORPS):
        brut = self.lire_corps(maximum)
        try:
            return json.loads(brut.decode("utf-8")) if brut else {}
        except (ValueError, UnicodeDecodeError):
            raise ValueError("JSON invalide")

    # --- routage -----------------------------------------------------------
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self.router("GET")

    def do_POST(self):
        self.router("POST")

    def do_PUT(self):
        self.router("PUT")

    def do_DELETE(self):
        self.router("DELETE")

    def router(self, methode):
        url = urlparse(self.path)
        chemin = unquote(url.path)
        self.query = parse_qs(url.query)
        try:
            if chemin.startswith("/admin/api/"):
                return self.api(methode, chemin[len("/admin/api"):])
            if methode not in ("GET", "HEAD"):
                return self.erreur(405, "Méthode non autorisée")
            if chemin in ("/admin", "/admin/"):
                return self.envoyer(200, admin_ui.PAGE, entetes=[("Cache-Control", "no-store"), ("X-Frame-Options", "DENY")])
            if chemin == "/":
                return self.envoyer(200, render.page_accueil(APP.store.lire_contenu(), APP.store.lister_pages()), entetes=[("Cache-Control", "public, max-age=300")])
            if chemin == "/healthz":
                return self.envoyer(200, "ok\n", "text/plain")
            if chemin == "/maj/mastermix2.json":
                return self.manifeste_maj()
            if chemin.startswith("/p/"):
                page = APP.store.lire_page(chemin[3:])
                if not page or not page.get("visible"):
                    return self.erreur(404, "Page introuvable")
                return self.envoyer(200, render.page_libre(APP.store.lire_contenu(), page, APP.store.lister_pages()), entetes=[("Cache-Control", "public, max-age=300")])
            return self.statique(chemin)
        except ValueError as e:
            return self.erreur(400, str(e))
        except (courrier.ErreurCourrier, mailu_api.ErreurMailu) as e:
            return self.erreur(502, str(e))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # noqa: BLE001 - dernier filet, on journalise sans exposer
            APP.store.journal(self.ip, "erreur interne %s: %r" % (self.path, e))
            return self.erreur(500, "Erreur interne")

    # --- mise à jour de MasterMix 2 -----------------------------------------
    def manifeste_maj(self):
        """Manifeste lu par MasterMix 2 au lancement (Aide > Vérifier les mises à jour).

        Construit depuis la section Téléchargement du contenu : la version est celle
        du nom de fichier publié (MasterMix-<version>-Setup-x64.exe), l'URL, la taille
        et l'empreinte SHA-256 sont celles affichées sur la page. 404 tant que le
        fichier publié n'est pas un installeur MasterMix 2.
        """
        t = APP.store.lire_contenu().get("telechargement", {})
        fichier = str(t.get("fichier") or "")
        m = re.fullmatch(r"MasterMix-(\d+(?:\.\d+)+)-Setup-x64\.exe", fichier)
        if not m or not m.group(1).startswith("2."):
            return self.erreur(404, "Aucune mise à jour publiée")
        try:
            taille = int(t.get("taille") or 0)
        except (TypeError, ValueError):
            taille = 0
        if taille <= 0 or not t.get("sha256"):
            return self.erreur(404, "Aucune mise à jour publiée")
        manifeste = {
            "version": m.group(1),
            "fichier": fichier,
            "url": "%s/telechargements/%s" % (SITE_URL, fichier),
            "taille": taille,
            "sha256": str(t["sha256"]).strip().lower(),
            "notes": str(t.get("notes_maj") or ""),
        }
        return self.json_(manifeste, entetes=[("Cache-Control", "no-store")])

    # --- statique ----------------------------------------------------------
    def statique(self, chemin):
        parties = [p for p in chemin.split("/") if p]
        if not parties or any(p in ("..", ".") or p.startswith(".") for p in parties):
            return self.erreur(404, "Introuvable")
        fichier = APP.www.joinpath(*parties)
        try:
            fichier.resolve().relative_to(APP.www.resolve())
        except ValueError:
            return self.erreur(404, "Introuvable")
        if not fichier.is_file() or fichier.suffix == ".tmp":
            return self.erreur(404, "Introuvable")
        type_, _ = mimetypes.guess_type(str(fichier))
        type_ = type_ or "application/octet-stream"
        if fichier.suffix == ".svg":
            type_ = "image/svg+xml"
        taille = fichier.stat().st_size
        entetes = [("Accept-Ranges", "bytes"), ("Cache-Control", "public, max-age=3600")]
        if parties[0] == "telechargements":
            type_ = "text/plain; charset=utf-8" if fichier.suffix == ".txt" else "application/octet-stream"
            if fichier.suffix != ".txt":
                entetes.append(("Content-Disposition", 'attachment; filename="%s"' % fichier.name))
        debut, fin = 0, taille - 1
        code = 200
        plage = self.headers.get("Range", "")
        m = re.match(r"bytes=(\d*)-(\d*)$", plage)
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                debut = int(m.group(1))
                if m.group(2):
                    fin = min(int(m.group(2)), taille - 1)
            else:
                debut = max(0, taille - int(m.group(2)))
            if debut > fin or debut >= taille:
                return self.envoyer(416, "", "text/plain", [("Content-Range", "bytes */%d" % taille)])
            code = 206
            entetes.append(("Content-Range", "bytes %d-%d/%d" % (debut, fin, taille)))
        longueur = fin - debut + 1
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(longueur))
        for k, v in entetes:
            self.send_header(k, v)
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(fichier, "rb") as f:
            f.seek(debut)
            reste = longueur
            while reste > 0:
                bloc = f.read(min(256 * 1024, reste))
                if not bloc:
                    break
                self.wfile.write(bloc)
                reste -= len(bloc)

    # --- API admin ---------------------------------------------------------
    def session(self):
        return APP.admin.session_valide(self.cookies().get("mm_session"))

    def api(self, methode, chemin):
        if methode == "POST" and chemin == "/connexion":
            return self.post_connexion()
        csrf = self.session()
        if not csrf:
            return self.json_({"erreur": "non connecté"}, 401)
        if methode != "GET" and not hmac.compare_digest(self.headers.get("X-CSRF", ""), csrf):
            return self.json_({"erreur": "jeton CSRF manquant ou invalide"}, 403)
        parties = [p for p in chemin.split("/") if p]
        nom = parties[0] if parties else ""
        routeur = getattr(self, "api_" + nom.replace("-", "_"), None)
        if not routeur:
            return self.json_({"erreur": "route inconnue"}, 404)
        return routeur(methode, parties[1:], csrf)

    def post_connexion(self):
        d = self.lire_json()
        try:
            resultat = APP.admin.connecter(d.get("mot_de_passe", ""), self.ip)
        except PermissionError as e:
            APP.store.journal(self.ip, "connexion bloquée")
            return self.json_({"erreur": str(e)}, 429)
        if not resultat:
            APP.store.journal(self.ip, "échec de connexion")
            return self.json_({"erreur": "mot de passe incorrect"}, 401)
        jeton, csrf = resultat
        APP.store.journal(self.ip, "connexion")
        return self.json_({"csrf": csrf}, entetes=[("Set-Cookie", "mm_session=%s; %s; Max-Age=%d" % (jeton, COOKIE_FLAGS, admin_mod.SESSION_DUREE))])

    def api_deconnexion(self, methode, parties, csrf):
        APP.admin.deconnecter()
        return self.json_({"ok": True}, entetes=[("Set-Cookie", "mm_session=; %s; Max-Age=0" % COOKIE_FLAGS)])

    def api_etat(self, methode, parties, csrf):
        return self.json_({"csrf": csrf, "mot_de_passe_initial": bool(APP.admin.mot_de_passe_initial), "domaine": DOMAINE, "site": SITE_URL})

    def api_contenu(self, methode, parties, csrf):
        if methode == "GET":
            return self.json_({"contenu": APP.store.lire_contenu(), "champs": render.CHAMPS})
        if methode == "PUT":
            contenu = self.lire_json()
            if not isinstance(contenu, dict) or not all(s in contenu for s in render.CHAMPS):
                raise ValueError("contenu incomplet")
            nom = APP.store.ecrire_contenu(contenu)
            APP.store.journal(self.ip, "contenu enregistré (%s)" % nom)
            return self.json_({"ok": True, "sauvegarde": nom})
        return self.json_({"erreur": "méthode"}, 405)

    def api_sauvegardes(self, methode, parties, csrf):
        if methode == "GET":
            return self.json_({"sauvegardes": APP.store.lister_sauvegardes()})
        if methode == "POST" and parties == ["restaurer"]:
            nom = self.lire_json().get("nom", "")
            try:
                APP.store.restaurer(nom)
            except FileNotFoundError:
                return self.json_({"erreur": "sauvegarde introuvable"}, 404)
            APP.store.journal(self.ip, "contenu restauré depuis %s" % nom)
            return self.json_({"ok": True})
        return self.json_({"erreur": "méthode"}, 405)

    def api_pages(self, methode, parties, csrf):
        if methode == "GET" and not parties:
            return self.json_({"pages": [{k: p.get(k) for k in ("slug", "titre", "visible", "ordre", "modifie")} for p in APP.store.lister_pages()]})
        if not parties:
            return self.json_({"erreur": "méthode"}, 405)
        slug = parties[0]
        if methode == "GET":
            page = APP.store.lire_page(slug)
            return self.json_(page) if page else self.json_({"erreur": "page introuvable"}, 404)
        if methode == "PUT":
            page = self.lire_json()
            page["slug"] = slug
            APP.store.ecrire_page(page)
            APP.store.journal(self.ip, "page enregistrée /p/%s" % slug)
            return self.json_({"ok": True})
        if methode == "DELETE":
            ok = APP.store.supprimer_page(slug)
            if ok:
                APP.store.journal(self.ip, "page supprimée /p/%s" % slug)
            return self.json_({"ok": ok}, 200 if ok else 404)
        return self.json_({"erreur": "méthode"}, 405)

    def api_fichiers(self, methode, parties, csrf):
        if not parties or parties[0] not in store_mod.CATEGORIES:
            return self.json_({"erreur": "catégorie inconnue"}, 404)
        cat = parties[0]
        if methode == "GET":
            return self.json_({"fichiers": APP.store.lister_fichiers(cat)})
        if methode == "DELETE" and len(parties) == 2:
            nom = parties[1]
            contenu = APP.store.lire_contenu()
            utilises = {contenu.get("accueil", {}).get("capture"), contenu.get("console", {}).get("capture"), contenu.get("telechargement", {}).get("fichier")}
            if nom in utilises:
                return self.json_({"erreur": "fichier utilisé par la page d'accueil : changez d'abord le contenu"}, 409)
            ok = APP.store.supprimer_fichier(cat, nom)
            if ok:
                APP.store.journal(self.ip, "fichier supprimé %s/%s" % (cat, nom))
            return self.json_({"ok": ok}, 200 if ok else 404)
        if methode == "POST" and parties[1:] == ["morceau"]:
            return self.morceau(cat)
        return self.json_({"erreur": "méthode"}, 405)

    def morceau(self, cat):
        q = {k: v[0] for k, v in self.query.items()}
        nom = store_mod.assainir_nom(q.get("nom", ""))
        ident = re.sub(r"[^a-z0-9]", "", q.get("id", ""))[:40]
        indice, total = int(q.get("indice", 0)), int(q.get("total", 1))
        if not ident or total < 1 or not 0 <= indice < total:
            raise ValueError("paramètres de téléversement invalides")
        if Path(nom).suffix.lower() not in EXTENSIONS[cat]:
            raise ValueError("extension refusée pour %s : %s" % (cat, ", ".join(sorted(EXTENSIONS[cat]))))
        donnees = self.lire_corps(MAX_MORCEAU)
        temporaire = APP.www / cat / (".%s.part" % ident)
        with APP._verrou:
            etat = APP.televersements.setdefault(ident, {"recu": 0, "taille": 0, "nom": nom, "debut": time.time()})
            if etat["recu"] != indice or etat["nom"] != nom:
                raise ValueError("morceau hors séquence")
            if etat["taille"] + len(donnees) > LIMITES[cat]:
                temporaire.unlink(missing_ok=True)
                APP.televersements.pop(ident, None)
                raise ValueError("fichier trop volumineux (%s max)" % render.format_taille(LIMITES[cat]))
            temporaire.parent.mkdir(parents=True, exist_ok=True)
            with open(temporaire, "ab" if indice else "wb") as f:
                f.write(donnees)
            etat["recu"] += 1
            etat["taille"] += len(donnees)
            if etat["recu"] < total:
                return self.json_({"ok": True, "recu": etat["recu"]})
            APP.televersements.pop(ident, None)
            if nom.lower().endswith(".svg") and _SVG_DANGER.search(temporaire.read_bytes()):
                temporaire.unlink(missing_ok=True)
                raise ValueError("SVG refusé : script ou gestionnaire d'événement détecté")
            final = APP.store.chemin_fichier(cat, nom)
            os.replace(temporaire, final)
        reponse = {"ok": True, "nom": final.name, "taille": final.stat().st_size}
        if cat == "telechargements":
            APP.store.regenerer_sha256sums()
            reponse["sha256"] = store_mod.sha256_fichier(final)
        APP.store.journal(self.ip, "fichier reçu %s/%s (%d octets)" % (cat, final.name, reponse["taille"]))
        return self.json_(reponse)

    def api_reglages(self, methode, parties, csrf):
        r = APP.store.lire_reglages()
        if methode == "GET":
            return self.json_({
                "mailu_url": r.get("mailu_url", ""), "mailu_jeton_defini": bool(r.get("mailu_jeton")),
                "hote": r.get("hote", courrier.REGLAGES_DEFAUT["hote"]), "nom_certificat": r.get("nom_certificat", courrier.REGLAGES_DEFAUT["nom_certificat"]),
                "sauvegardes": APP.store.lister_sauvegardes(), "journal": APP.store.lire_journal(),
            })
        if methode == "PUT":
            d = self.lire_json()
            r["mailu_url"] = str(d.get("mailu_url", "")).strip().rstrip("/")
            if d.get("mailu_jeton"):
                r["mailu_jeton"] = secrets_box.chiffrer(APP.cle, str(d["mailu_jeton"]).strip())
            r["hote"] = str(d.get("hote", "")).strip() or courrier.REGLAGES_DEFAUT["hote"]
            r["nom_certificat"] = str(d.get("nom_certificat", "")).strip() or courrier.REGLAGES_DEFAUT["nom_certificat"]
            APP.store.ecrire_reglages(r)
            APP.store.journal(self.ip, "réglages enregistrés")
            return self.json_({"ok": True})
        if methode == "POST" and parties == ["tester-mailu"]:
            domaine = APP.mailu().verifier()
            return self.json_({"ok": True, "domaine": (domaine or {}).get("name", DOMAINE)})
        return self.json_({"erreur": "méthode"}, 405)

    def api_mot_de_passe(self, methode, parties, csrf):
        d = self.lire_json()
        try:
            APP.admin.changer_mot_de_passe(d.get("ancien", ""), d.get("nouveau", ""))
        except ValueError as e:
            return self.json_({"erreur": str(e)}, 400)
        APP.store.journal(self.ip, "mot de passe admin changé")
        return self.json_({"ok": True})

    def api_journal(self, methode, parties, csrf):
        return self.json_({"journal": APP.store.lire_journal()})

    # --- adresses ------------------------------------------------------------
    def api_adresses(self, methode, parties, csrf):
        connues = APP.boites_connues()
        if methode == "GET" and parties == ["ouvrables"]:
            return self.json_({"boites": [{"email": e, "nom": i.get("nom", "")} for e, i in sorted(connues.items())]})
        if methode == "GET" and not parties:
            api = APP.mailu()
            boites = api.lister_boites()
            for b in boites:
                b["ouvrable"] = b["email"] in connues
            return self.json_({"boites": boites, "alias": api.lister_alias()})
        if methode == "POST" and not parties:
            d = self.lire_json()
            local = str(d.get("local", "")).strip().lower()
            mdp = str(d.get("mot_de_passe", "")).strip()
            genere = not mdp
            if genere:
                mdp = admin_mod.generer_mot_de_passe(16)
            elif len(mdp) < admin_mod.MOT_DE_PASSE_MIN:
                return self.json_({"erreur": "mot de passe : %d caractères minimum" % admin_mod.MOT_DE_PASSE_MIN}, 400)
            email = APP.mailu().creer_boite(local, mdp, nom=str(d.get("nom", "")).strip(), quota=int(d.get("quota") or 1024 ** 3))
            APP.enregistrer_boite(email, mdp, str(d.get("nom", "")).strip())
            APP.store.journal(self.ip, "boîte créée %s" % email)
            return self.json_({"ok": True, "email": email, "mot_de_passe": mdp if genere else None})
        if len(parties) == 2 and methode == "POST":
            email, action = parties
            if not email.endswith("@" + DOMAINE):
                return self.json_({"erreur": "adresse hors domaine"}, 400)
            d = self.lire_json()
            if action == "mot-de-passe":
                mdp = str(d.get("mot_de_passe", "")).strip() or admin_mod.generer_mot_de_passe(16)
                if len(mdp) < admin_mod.MOT_DE_PASSE_MIN:
                    return self.json_({"erreur": "mot de passe : %d caractères minimum" % admin_mod.MOT_DE_PASSE_MIN}, 400)
                APP.mailu().changer_mot_de_passe(email, mdp)
                APP.enregistrer_boite(email, mdp)
                APP.store.journal(self.ip, "mot de passe réinitialisé %s" % email)
                return self.json_({"ok": True, "mot_de_passe": mdp})
            if action == "rattacher":
                mdp = str(d.get("mot_de_passe", ""))
                courrier.verifier_identifiants(APP.reglages_courrier(), email, mdp, fabrique=FABRIQUES["imap"])
                APP.enregistrer_boite(email, mdp)
                APP.store.journal(self.ip, "boîte rattachée %s" % email)
                return self.json_({"ok": True})
        if len(parties) == 1 and methode == "DELETE":
            email = parties[0]
            if not email.endswith("@" + DOMAINE):
                return self.json_({"erreur": "adresse hors domaine"}, 400)
            APP.mailu().supprimer_boite(email)
            APP.oublier_boite(email)
            APP.store.journal(self.ip, "boîte supprimée %s" % email)
            return self.json_({"ok": True})
        return self.json_({"erreur": "route inconnue"}, 404)

    def api_alias(self, methode, parties, csrf):
        if methode == "POST" and not parties:
            d = self.lire_json()
            email = APP.mailu().creer_alias(str(d.get("local", "")).strip().lower(), [str(x) for x in d.get("destinations", [])])
            APP.store.journal(self.ip, "alias créé %s" % email)
            return self.json_({"ok": True, "email": email})
        if methode == "DELETE" and len(parties) == 1:
            if not parties[0].endswith("@" + DOMAINE):
                return self.json_({"erreur": "adresse hors domaine"}, 400)
            APP.mailu().supprimer_alias(parties[0])
            APP.store.journal(self.ip, "alias supprimé %s" % parties[0])
            return self.json_({"ok": True})
        return self.json_({"erreur": "route inconnue"}, 404)

    # --- courrier ------------------------------------------------------------
    def api_courrier(self, methode, parties, csrf):
        if len(parties) < 2:
            return self.json_({"erreur": "route inconnue"}, 404)
        email, dossier = parties[0], parties[1]
        boite, info = APP.boite(email)
        if methode == "POST" and dossier == "envoyer":
            return self.envoyer_message(boite, info)
        if dossier not in courrier.DOSSIERS:
            return self.json_({"erreur": "dossier inconnu"}, 404)
        if methode == "GET" and len(parties) == 2:
            return self.json_({"messages": boite.lister(dossier)})
        if len(parties) >= 3:
            id_ = parties[2]
            if methode == "GET" and len(parties) == 3:
                message, brut = boite.lire(dossier, id_)
                message["citation"] = courrier.citer(message)
                return self.json_(message)
            if methode == "GET" and len(parties) == 5 and parties[3] == "piece":
                _, brut = boite.lire(dossier, id_)
                nom, type_, octets = courrier.extraire_piece(brut, parties[4])
                nom = store_mod.assainir_nom(nom)
                return self.envoyer(200, octets, "application/octet-stream", [("Content-Disposition", 'attachment; filename="%s"' % nom)])
            if methode == "POST" and len(parties) == 4 and parties[3] == "lu":
                boite.marquer(dossier, id_, bool(self.lire_json().get("lu", True)))
                return self.json_({"ok": True})
            if methode == "DELETE" and len(parties) == 3:
                boite.supprimer(dossier, id_)
                APP.store.journal(self.ip, "message supprimé %s/%s/%s" % (email, dossier, id_))
                return self.json_({"ok": True})
        return self.json_({"erreur": "route inconnue"}, 404)

    def envoyer_message(self, boite, info):
        d = self.lire_json(MAX_ENVOI)
        pieces = []
        for p in d.get("pieces", []) or []:
            try:
                octets = base64.b64decode(p.get("b64", ""), validate=True)
            except (ValueError, TypeError):
                raise ValueError("pièce jointe illisible")
            pieces.append((store_mod.assainir_nom(p.get("nom", "piece")), str(p.get("type") or "application/octet-stream"), octets))
        source = d.get("transfert_de") or {}
        if source.get("id") and source.get("dossier") in courrier.DOSSIERS:
            message, brut = boite.lire(source["dossier"], source["id"])
            for piece in message["pieces"]:
                pieces.append(courrier.extraire_piece(brut, piece["indice"]))
        mid = boite.envoyer(info.get("nom", ""), str(d.get("a", "")), str(d.get("sujet", "")), str(d.get("texte", "")),
                            cc=str(d.get("cc", "")), pieces=pieces, en_reponse_a=d.get("en_reponse_a") or None, references=d.get("references") or None)
        APP.store.journal(self.ip, "message envoyé de %s à %s : %s" % (boite.email, d.get("a", ""), d.get("sujet", "")))
        return self.json_({"ok": True, "message_id": mid})


def creer_serveur(hote, port, data_dir, www_dir):
    global APP
    APP = Application(data_dir, www_dir)
    return ThreadingHTTPServer((hote, port), Handler)


def main():
    data_dir = os.environ.get("MM_DATA", str(Path(__file__).resolve().parents[1] / "data"))
    www_dir = os.environ.get("MM_WWW", str(Path(__file__).resolve().parents[1] / "www"))
    serveur = creer_serveur(HOST, PORT, data_dir, www_dir)
    print("mastermix.fr : http://%s:%d/  (données %s, www %s)" % (HOST, PORT, data_dir, www_dir), flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
