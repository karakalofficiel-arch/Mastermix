# mastermix.fr backoffice et courrier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer le site statique mastermix.fr par un serveur Python autonome qui rend la page depuis un contenu éditable, offre un backoffice `/admin` (sections, pages libres, fichiers) et gère le courrier de toutes les boîtes `@mastermix.fr` via Mailu (IMAP, SMTP, API).

**Architecture:** Un seul processus `ThreadingHTTPServer` (bibliothèque standard) dans un conteneur `python:3.12-alpine` sur `192.168.1.166:8095`, derrière le relais nginx `.117` inchangé. Données en JSON sous `data/`, fichiers publics sous `www/`. Modules à responsabilité unique : `store`, `secrets_box`, `admin`, `markdown_lite`, `render`, `mailu_api`, `courrier`, `admin_ui`, `server`.

**Tech Stack:** Python 3.12, bibliothèque standard uniquement (`http.server`, `json`, `hashlib`, `hmac`, `imaplib`, `smtplib`, `email`, `urllib.request`, `unittest`). Docker Compose v2 sur .166. Mailu 2024.06 (API REST v1).

**Spec:** `docs/superpowers/specs/2026-09-15-mastermix-site-admin-courrier-design.md`

## Global Constraints

- Bibliothèque standard Python uniquement ; aucun `pip install`.
- Code, commentaires et textes d'interface en français ; identifiants de code en anglais ou français cohérents par module (le patron karakal.media est en français : on garde le français).
- Le conteneur écoute sur `0.0.0.0:8095` dans le conteneur, publié `192.168.1.166:8095` ; le relais .117 n'est pas modifié sauf `client_max_body_size 2m`.
- Chemins par variables d'environnement : `MM_DATA` (défaut `./data`), `MM_WWW` (défaut `./www`), `MM_HOST` (défaut `127.0.0.1`), `MM_PORT` (défaut `8095`), `MM_SITE_URL` (défaut `https://mastermix.fr`), `MM_DEV` (`1` retire `Secure` du cookie).
- Cookie de session `mm_session` : `HttpOnly; Secure; SameSite=Strict`, 12 h d'inactivité, une seule session active.
- CSRF : en-tête `X-CSRF` obligatoire sur POST/PUT/DELETE de l'admin.
- Limites : corps 512 Ko sauf téléversements ; morceaux de 1 Mo ; images 8 Mo ; installeurs 200 Mo ; pièces jointes 20 Mo au total.
- Écritures JSON atomiques (temporaire + `os.replace`) sous verrou, 30 sauvegardes horodatées conservées.
- Aucune ressource externe dans l'admin. Page publique : polices Google (Syne, Manrope) uniquement, comme aujourd'hui.
- Tests : `python -m unittest discover -s site/app/tests -v` doit passer à la fin de chaque tâche. Commits à chaque tâche, messages en français préfixés (`feat(site)`, `test(site)`, `chore(site)`), terminés par les lignes `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` et `Claude-Session: https://claude.ai/code/session_01HM9hUkUvK7EJ593QJS8WCV`.
- Ne jamais afficher ni journaliser un mot de passe ou le jeton Mailu.

## File Structure

```
site/app/
  server.py          routage HTTP public + admin, sessions, CSRF, limites, téléversements
  render.py          HTML public (page d'accueil, pages libres) depuis le contenu ; CONTENU_DEFAUT
  markdown_lite.py   Markdown simplifié -> HTML sûr
  store.py           JSON atomique, sauvegardes, pages, fichiers, journal
  admin.py           compte admin, sessions, blocage, CSRF
  admin_ui.py        HTML/CSS/JS du backoffice (chaîne statique)
  secrets_box.py     chiffrement authentifié des mots de passe de boîtes
  mailu_api.py       client API Mailu (boîtes, alias, mot de passe)
  courrier.py        IMAP (liste, lecture, drapeaux, suppression) et SMTP (envoi, copie Envoyés)
  tests/
    test_store.py test_secrets_box.py test_admin.py test_markdown_lite.py test_render.py
    test_server_public.py test_server_admin.py test_mailu_api.py test_courrier.py
site/nas166/docker-compose.yml        (modifié : service python)
site/nas166/docker-compose.nginx.yml  (ancien compose, rollback)
site/deploy.sh                        (modifié : envoie app/ et data/ initial)
site/README.md                        (modifié : exploitation admin/courrier)
```

Interfaces communes (utilisées par plusieurs tâches) :

```python
# store.py
class Store:
    def __init__(self, data_dir: Path, www_dir: Path): ...
    def lire_contenu(self) -> dict            # content.json ou CONTENU_DEFAUT copié au premier appel
    def ecrire_contenu(self, contenu: dict) -> str   # renvoie le nom de la sauvegarde créée
    def lister_sauvegardes(self) -> list[str]
    def restaurer(self, nom: str) -> None
    def lister_pages(self) -> list[dict]       # triées par ordre, puis slug
    def lire_page(self, slug: str) -> dict | None
    def ecrire_page(self, page: dict) -> None  # valide slug, crée ou remplace
    def supprimer_page(self, slug: str) -> bool
    def lire_reglages(self) -> dict            # settings.json (mode 600), {} si absent
    def ecrire_reglages(self, reglages: dict) -> None
    def journal(self, ip: str, action: str) -> None
    def lire_journal(self, n: int = 200) -> list[str]
    def lister_fichiers(self, categorie: str) -> list[dict]   # "media" | "telechargements" ; {nom, taille, sha256?}
    def chemin_fichier(self, categorie: str, nom: str) -> Path # assaini, sous www/<categorie>/
    def supprimer_fichier(self, categorie: str, nom: str) -> bool
    def regenerer_sha256sums(self) -> None
```

---

### Task 1: Squelette, `store.py` (contenu, sauvegardes, pages, réglages, journal)

**Files:**
- Create: `site/app/__init__.py` (vide), `site/app/store.py`, `site/app/tests/__init__.py` (vide), `site/app/tests/test_store.py`

**Interfaces:**
- Produces: la classe `Store` décrite dans « File Structure ». `store.assainir_nom(nom: str) -> str` (lettres, chiffres, `.`, `-`, `_` ; le reste devient `-` ; 1 à 120 caractères ; jamais `..`). `store.valider_slug(slug: str) -> bool` (`^[a-z0-9-]{1,60}$`). Le contenu par défaut vient de `render.CONTENU_DEFAUT` (Task 5) ; jusqu'à Task 5, `Store.__init__` accepte `contenu_defaut: dict` et la valeur par défaut est `{}`.

- [ ] **Step 1: Write the failing tests**

```python
# site/app/tests/test_store.py
import json, os, tempfile, unittest
from pathlib import Path
from app import store as store_mod
from app.store import Store, assainir_nom, valider_slug

class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.data = base / "data"; self.www = base / "www"
        self.store = Store(self.data, self.www, contenu_defaut={"site": {"titre": "MasterMix"}})

    def tearDown(self):
        self.tmp.cleanup()

    def test_contenu_defaut_copie_au_premier_appel(self):
        self.assertEqual(self.store.lire_contenu()["site"]["titre"], "MasterMix")
        self.assertTrue((self.data / "content.json").exists())

    def test_ecriture_atomique_et_sauvegarde(self):
        nom = self.store.ecrire_contenu({"site": {"titre": "Nouveau"}})
        self.assertEqual(self.store.lire_contenu()["site"]["titre"], "Nouveau")
        self.assertIn(nom, self.store.lister_sauvegardes())
        self.assertFalse(list(self.data.glob("*.tmp")))

    def test_rotation_30_sauvegardes(self):
        for i in range(35):
            self.store.ecrire_contenu({"i": i})
        self.assertEqual(len(self.store.lister_sauvegardes()), 30)

    def test_restaurer(self):
        self.store.ecrire_contenu({"v": 1})
        nom = self.store.ecrire_contenu({"v": 2})
        self.store.ecrire_contenu({"v": 3})
        self.store.restaurer(nom)
        self.assertEqual(self.store.lire_contenu()["v"], 2)

    def test_pages(self):
        self.store.ecrire_page({"slug": "actus", "titre": "Actus", "contenu_md": "# A", "visible": True, "ordre": 2})
        self.store.ecrire_page({"slug": "aide", "titre": "Aide", "contenu_md": "", "visible": False, "ordre": 1})
        slugs = [p["slug"] for p in self.store.lister_pages()]
        self.assertEqual(slugs, ["aide", "actus"])
        self.assertEqual(self.store.lire_page("actus")["titre"], "Actus")
        self.assertIsNone(self.store.lire_page("inconnue"))
        self.assertTrue(self.store.supprimer_page("aide"))
        self.assertFalse(self.store.supprimer_page("aide"))

    def test_page_slug_invalide(self):
        with self.assertRaises(ValueError):
            self.store.ecrire_page({"slug": "../x", "titre": "x", "contenu_md": "", "visible": True, "ordre": 0})

    def test_reglages_mode_600(self):
        self.store.ecrire_reglages({"jeton": "abc"})
        self.assertEqual(self.store.lire_reglages()["jeton"], "abc")
        if os.name != "nt":
            self.assertEqual(oct((self.data / "settings.json").stat().st_mode & 0o777), "0o600")

    def test_journal(self):
        self.store.journal("1.2.3.4", "connexion")
        lignes = self.store.lire_journal()
        self.assertEqual(len(lignes), 1)
        self.assertIn("1.2.3.4", lignes[0]); self.assertIn("connexion", lignes[0])

    def test_fichiers(self):
        (self.www / "media").mkdir(parents=True)
        (self.www / "media" / "a.png").write_bytes(b"x" * 10)
        self.assertEqual(self.store.lister_fichiers("media")[0]["taille"], 10)
        self.assertEqual(self.store.chemin_fichier("media", "../a.png").name, "a.png")
        with self.assertRaises(ValueError):
            self.store.chemin_fichier("autre", "a.png")
        self.assertTrue(self.store.supprimer_fichier("media", "a.png"))

    def test_sha256sums(self):
        d = self.www / "telechargements"; d.mkdir(parents=True)
        (d / "x.exe").write_bytes(b"abc")
        self.store.regenerer_sha256sums()
        texte = (d / "SHA256SUMS.txt").read_text()
        self.assertIn("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad *x.exe", texte)
        self.assertEqual(self.store.lister_fichiers("telechargements")[0]["sha256"][:8], "ba7816bf")

class TestUtilitaires(unittest.TestCase):
    def test_assainir_nom(self):
        self.assertEqual(assainir_nom("Mon Fichier (1).PNG"), "Mon-Fichier-1-.PNG")
        self.assertEqual(assainir_nom("../../etc/passwd"), "etc-passwd")
        self.assertEqual(assainir_nom(""), "fichier")
    def test_valider_slug(self):
        self.assertTrue(valider_slug("actualites-2026"))
        self.assertFalse(valider_slug("Actus")); self.assertFalse(valider_slug("a/b")); self.assertFalse(valider_slug(""))
```

- [ ] **Step 2: Run tests to verify they fail**

Run (depuis `A:/claude/mastermix/site`) : `python -m unittest app.tests.test_store -v`
Expected: `ModuleNotFoundError: No module named 'app.store'`

- [ ] **Step 3: Write `store.py`**

```python
# site/app/store.py
"""Persistance JSON de mastermix.fr : contenu, pages, réglages, journal, fichiers.

Écritures atomiques (fichier temporaire puis os.replace) sous verrou ; chaque
sauvegarde du contenu dépose une copie horodatée dans data/backups (30 gardées).
"""
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

SAUVEGARDES_MAX = 30
JOURNAL_MAX_OCTETS = 1024 * 1024
CATEGORIES = ("media", "telechargements")
_SLUG = re.compile(r"^[a-z0-9-]{1,60}$")
_NOM_OK = re.compile(r"[^A-Za-z0-9._-]+")


def assainir_nom(nom):
    nom = os.path.basename(nom.replace("\\", "/"))
    nom = _NOM_OK.sub("-", nom).strip("-.")
    while ".." in nom:
        nom = nom.replace("..", ".")
    return (nom or "fichier")[:120]


def valider_slug(slug):
    return bool(_SLUG.match(slug or ""))


def _ecrire_atomique(chemin, texte, mode=None):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(chemin.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
        f.flush()
        os.fsync(f.fileno())
    if mode is not None and os.name != "nt":
        os.chmod(tmp, mode)
    os.replace(tmp, chemin)


def _lire_json(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


class Store:
    def __init__(self, data_dir, www_dir, contenu_defaut=None):
        self.data = Path(data_dir)
        self.www = Path(www_dir)
        self.contenu_defaut = contenu_defaut or {}
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "pages").mkdir(exist_ok=True)
        (self.data / "backups").mkdir(exist_ok=True)
        self._verrou = threading.RLock()

    # --- contenu -----------------------------------------------------------
    def lire_contenu(self):
        with self._verrou:
            chemin = self.data / "content.json"
            if not chemin.exists():
                _ecrire_atomique(chemin, json.dumps(self.contenu_defaut, ensure_ascii=False, indent=2))
            return _lire_json(chemin, dict(self.contenu_defaut))

    def ecrire_contenu(self, contenu):
        with self._verrou:
            nom = time.strftime("content-%Y%m%d-%H%M%S") + "-%03d.json" % (int(time.time() * 1000) % 1000)
            texte = json.dumps(contenu, ensure_ascii=False, indent=2)
            _ecrire_atomique(self.data / "backups" / nom, texte)
            _ecrire_atomique(self.data / "content.json", texte)
            for ancien in self.lister_sauvegardes()[SAUVEGARDES_MAX:]:
                (self.data / "backups" / ancien).unlink(missing_ok=True)
            return nom

    def lister_sauvegardes(self):
        return sorted((p.name for p in (self.data / "backups").glob("content-*.json")), reverse=True)

    def restaurer(self, nom):
        with self._verrou:
            nom = assainir_nom(nom)
            source = self.data / "backups" / nom
            if not source.exists():
                raise FileNotFoundError(nom)
            self.ecrire_contenu(_lire_json(source, {}))

    # --- pages -------------------------------------------------------------
    def lister_pages(self):
        pages = [_lire_json(p, None) for p in (self.data / "pages").glob("*.json")]
        pages = [p for p in pages if p]
        return sorted(pages, key=lambda p: (int(p.get("ordre", 0)), p.get("slug", "")))

    def lire_page(self, slug):
        if not valider_slug(slug):
            return None
        return _lire_json(self.data / "pages" / (slug + ".json"), None)

    def ecrire_page(self, page):
        slug = page.get("slug", "")
        if not valider_slug(slug):
            raise ValueError("slug invalide")
        with self._verrou:
            ancien = self.lire_page(slug) or {}
            maintenant = int(time.time())
            page = {
                "slug": slug,
                "titre": str(page.get("titre", ""))[:200],
                "contenu_md": str(page.get("contenu_md", ""))[:200000],
                "visible": bool(page.get("visible", False)),
                "ordre": int(page.get("ordre", 0)),
                "cree": ancien.get("cree", maintenant),
                "modifie": maintenant,
            }
            _ecrire_atomique(self.data / "pages" / (slug + ".json"), json.dumps(page, ensure_ascii=False, indent=2))

    def supprimer_page(self, slug):
        if not valider_slug(slug):
            return False
        chemin = self.data / "pages" / (slug + ".json")
        if not chemin.exists():
            return False
        chemin.unlink()
        return True

    # --- réglages ----------------------------------------------------------
    def lire_reglages(self):
        return _lire_json(self.data / "settings.json", {})

    def ecrire_reglages(self, reglages):
        with self._verrou:
            _ecrire_atomique(self.data / "settings.json", json.dumps(reglages, ensure_ascii=False, indent=2), mode=0o600)

    # --- journal -----------------------------------------------------------
    def journal(self, ip, action):
        with self._verrou:
            chemin = self.data / "journal.log"
            if chemin.exists() and chemin.stat().st_size > JOURNAL_MAX_OCTETS:
                os.replace(chemin, chemin.with_suffix(".log.1"))
            with open(chemin, "a", encoding="utf-8") as f:
                f.write("%s %s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), ip, action.replace("\n", " ")))

    def lire_journal(self, n=200):
        chemin = self.data / "journal.log"
        if not chemin.exists():
            return []
        with open(chemin, encoding="utf-8") as f:
            return [l.rstrip("\n") for l in f.readlines()[-n:]]

    # --- fichiers ----------------------------------------------------------
    def _dossier(self, categorie):
        if categorie not in CATEGORIES:
            raise ValueError("catégorie inconnue")
        d = self.www / categorie
        d.mkdir(parents=True, exist_ok=True)
        return d

    def chemin_fichier(self, categorie, nom):
        return self._dossier(categorie) / assainir_nom(nom)

    def lister_fichiers(self, categorie):
        d = self._dossier(categorie)
        sommes = {}
        if categorie == "telechargements":
            sommes = self._lire_sommes()
        resultat = []
        for p in sorted(d.iterdir()):
            if not p.is_file() or p.name == "SHA256SUMS.txt":
                continue
            entree = {"nom": p.name, "taille": p.stat().st_size, "modifie": int(p.stat().st_mtime)}
            if p.name in sommes:
                entree["sha256"] = sommes[p.name]
            resultat.append(entree)
        return resultat

    def supprimer_fichier(self, categorie, nom):
        chemin = self.chemin_fichier(categorie, nom)
        if not chemin.exists():
            return False
        chemin.unlink()
        if categorie == "telechargements":
            self.regenerer_sha256sums()
        return True

    def _lire_sommes(self):
        chemin = self.www / "telechargements" / "SHA256SUMS.txt"
        sommes = {}
        if chemin.exists():
            for ligne in chemin.read_text(encoding="utf-8").splitlines():
                parties = ligne.split(" *", 1)
                if len(parties) == 2:
                    sommes[parties[1]] = parties[0]
        return sommes

    def regenerer_sha256sums(self):
        d = self._dossier("telechargements")
        lignes = []
        for p in sorted(d.iterdir()):
            if p.is_file() and p.name != "SHA256SUMS.txt":
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for bloc in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(bloc)
                lignes.append("%s *%s" % (h.hexdigest(), p.name))
        _ecrire_atomique(d / "SHA256SUMS.txt", "\n".join(lignes) + ("\n" if lignes else ""))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest app.tests.test_store -v`
Expected: `OK` (12 tests)

- [ ] **Step 5: Commit**

```bash
git add site/app/__init__.py site/app/store.py site/app/tests/__init__.py site/app/tests/test_store.py
git commit -m "feat(site): store JSON atomique, sauvegardes, pages, réglages, journal, fichiers"
```

---

### Task 2: `secrets_box.py` (chiffrement authentifié des mots de passe)

**Files:**
- Create: `site/app/secrets_box.py`, `site/app/tests/test_secrets_box.py`

**Interfaces:**
- Produces: `charger_cle(data_dir: Path) -> bytes` (lit ou crée `data/.cle`, 32 octets, mode 600) ; `chiffrer(cle: bytes, texte: str) -> str` (chaîne `v1:<hex nonce>:<hex etiquette>:<hex chiffre>`) ; `dechiffrer(cle: bytes, boite: str) -> str` (lève `ValueError` si altéré ou clé différente).

- [ ] **Step 1: Write the failing tests**

```python
# site/app/tests/test_secrets_box.py
import os, tempfile, unittest
from pathlib import Path
from app.secrets_box import charger_cle, chiffrer, dechiffrer

class TestSecretsBox(unittest.TestCase):
    def test_cle_creee_puis_relue(self):
        with tempfile.TemporaryDirectory() as d:
            k1 = charger_cle(Path(d)); k2 = charger_cle(Path(d))
            self.assertEqual(len(k1), 32); self.assertEqual(k1, k2)
            if os.name != "nt":
                self.assertEqual(oct((Path(d) / ".cle").stat().st_mode & 0o777), "0o600")

    def test_aller_retour(self):
        cle = os.urandom(32)
        boite = chiffrer(cle, "Mot de p@sse ünïcode")
        self.assertTrue(boite.startswith("v1:"))
        self.assertEqual(dechiffrer(cle, boite), "Mot de p@sse ünïcode")

    def test_nonce_different_a_chaque_fois(self):
        cle = os.urandom(32)
        self.assertNotEqual(chiffrer(cle, "x"), chiffrer(cle, "x"))

    def test_alteration_detectee(self):
        cle = os.urandom(32)
        boite = chiffrer(cle, "secret")
        parties = boite.split(":")
        parties[3] = ("0" if parties[3][0] != "0" else "1") + parties[3][1:]
        with self.assertRaises(ValueError):
            dechiffrer(cle, ":".join(parties))

    def test_mauvaise_cle(self):
        boite = chiffrer(os.urandom(32), "secret")
        with self.assertRaises(ValueError):
            dechiffrer(os.urandom(32), boite)

    def test_format_invalide(self):
        with self.assertRaises(ValueError):
            dechiffrer(os.urandom(32), "n'importe quoi")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest app.tests.test_secrets_box -v`
Expected: `ModuleNotFoundError: No module named 'app.secrets_box'`

- [ ] **Step 3: Write `secrets_box.py`**

```python
# site/app/secrets_box.py
"""Chiffrement authentifié des mots de passe de boîtes, bibliothèque standard.

Clé maîtresse de 32 octets dans data/.cle. Deux sous-clés dérivées (HKDF-SHA256) :
chiffrement (flux SHA-256 en mode compteur, XOR) et authentification (HMAC-SHA256
sur nonce + chiffré, vérifié avant tout déchiffrement). Format :
    v1:<nonce hex>:<étiquette hex>:<chiffré hex>
"""
import hashlib
import hmac
import os
from pathlib import Path

VERSION = "v1"


def charger_cle(data_dir):
    chemin = Path(data_dir) / ".cle"
    if chemin.exists():
        cle = chemin.read_bytes()
        if len(cle) == 32:
            return cle
    cle = os.urandom(32)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        f.write(cle)
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    os.replace(tmp, chemin)
    return cle


def _hkdf(cle, info):
    prk = hmac.new(b"mastermix-secrets-box", cle, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()


def _flux(cle_chiffrement, nonce, longueur):
    sortie = bytearray()
    compteur = 0
    while len(sortie) < longueur:
        sortie += hashlib.sha256(cle_chiffrement + nonce + compteur.to_bytes(4, "big")).digest()
        compteur += 1
    return bytes(sortie[:longueur])


def chiffrer(cle, texte):
    kc, ka = _hkdf(cle, b"chiffrement"), _hkdf(cle, b"authentification")
    nonce = os.urandom(16)
    clair = texte.encode("utf-8")
    chiffre = bytes(a ^ b for a, b in zip(clair, _flux(kc, nonce, len(clair))))
    etiquette = hmac.new(ka, nonce + chiffre, hashlib.sha256).digest()
    return ":".join([VERSION, nonce.hex(), etiquette.hex(), chiffre.hex()])


def dechiffrer(cle, boite):
    try:
        version, nonce_hex, etiquette_hex, chiffre_hex = boite.split(":")
        nonce, etiquette, chiffre = bytes.fromhex(nonce_hex), bytes.fromhex(etiquette_hex), bytes.fromhex(chiffre_hex)
    except (ValueError, AttributeError):
        raise ValueError("format de secret invalide")
    if version != VERSION or len(nonce) != 16:
        raise ValueError("format de secret invalide")
    kc, ka = _hkdf(cle, b"chiffrement"), _hkdf(cle, b"authentification")
    attendu = hmac.new(ka, nonce + chiffre, hashlib.sha256).digest()
    if not hmac.compare_digest(attendu, etiquette):
        raise ValueError("secret altéré ou clé incorrecte")
    clair = bytes(a ^ b for a, b in zip(chiffre, _flux(kc, nonce, len(chiffre))))
    return clair.decode("utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest app.tests.test_secrets_box -v`
Expected: `OK` (6 tests)

- [ ] **Step 5: Commit**

```bash
git add site/app/secrets_box.py site/app/tests/test_secrets_box.py
git commit -m "feat(site): chiffrement authentifié des secrets de boîtes"
```

---

### Tâches 3 à 12 (exécution directe demandée par l'utilisateur le 2026-09-15 16:28)

Sur instruction « déploie », les tâches suivantes sont implémentées directement depuis le spec, dans cet ordre, chacune avec ses tests avant le code et un commit :

3. `admin.py` : pbkdf2, sessions, blocage 5 échecs/15 min, CSRF, mot de passe initial.
4. `markdown_lite.py` : Markdown simplifié vers HTML sûr.
5. `render.py` : `CONTENU_DEFAUT` = page actuelle ; rendu accueil + pages libres ; test d'identité avec `site/www/index.html`.
6. `mailu_api.py` : client API (liste, création, mot de passe, suppression, alias) testé contre un serveur HTTP factice.
7. `courrier.py` : IMAP/SMTP avec doubles de test.
8. `admin_ui.py` : backoffice statique.
9. `server.py` : routes publiques, admin, contenu, pages, fichiers (morceaux), courrier, adresses, réglages ; tests HTTP.
10. `site/nas166/docker-compose.yml` (python), `docker-compose.nginx.yml` (rollback), `site/deploy.sh`, `site/README.md`.
11. Mailu : `API=true` + jeton, redémarrage `admin` ; relais .117 `client_max_body_size 2m`.
12. Recette en production (spec §8), création de `contact@mastermix.fr`.
