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
    nom = os.path.basename((nom or "").replace("\\", "/"))
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


def sha256_fichier(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


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
            return _lire_json(chemin, json.loads(json.dumps(self.contenu_defaut)))

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
                "ordre": int(page.get("ordre", 0) or 0),
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
                f.write("%s %s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), ip, str(action).replace("\n", " ")))

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
        sommes = self._lire_sommes() if categorie == "telechargements" else {}
        resultat = []
        for p in sorted(d.iterdir()):
            if not p.is_file() or p.name == "SHA256SUMS.txt" or p.suffix == ".tmp":
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
            if p.is_file() and p.name != "SHA256SUMS.txt" and p.suffix != ".tmp":
                lignes.append("%s *%s" % (sha256_fichier(p), p.name))
        _ecrire_atomique(d / "SHA256SUMS.txt", "\n".join(lignes) + ("\n" if lignes else ""))
