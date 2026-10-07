#!/usr/bin/env python3
"""Passe le contenu en ligne (data/content.json) de treize à dix plugins Mastersuite.

À lancer sur .166, une fois, après le déploiement du 2026-10-07 :

    ssh karakal166 "sudo python3 - < site/nas166/contenu-dix-plugins.py"   # depuis le poste

Retire MasterBend, MasterDrum et MasterString de la liste des plugins (décision
d'Ahmed du 2026-10-07 : « pour le moment »), remplace « treize » par « dix » dans
les textes et aligne la carte « Masteriser » sur la liste. Sauvegarde d'abord
dans data/backups/, puis écrit content.json atomiquement avec les droits du
conteneur (uid 1000). Idempotent.
"""
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

DATA = Path(os.environ.get("MM_DATA", "/mnt/karakalia/mastermix-site/data"))
CHEMIN = DATA / "content.json"
RETIRES = {"MasterBend", "MasterDrum", "MasterString"}
CARTE_MASTERISER = (
    "Les dix plugins Mastersuite sont inclus : égaliseur MasterQ, compresseur MasterComp 76, "
    "limiteur true-peak MasterL, restauration MasterClean, assistant de mastering MasterFlem, "
    "réverbe MasteRev, délai MasterDelay, accordeur MasterTune, et deux instruments : piano "
    "MasterKeys et basse MasterBass."
)


def dix(texte):
    if not isinstance(texte, str):
        return texte
    texte = re.sub(r"\bTreize\b", "Dix", texte)
    texte = re.sub(r"\btreize\b", "dix", texte)
    texte = texte.replace("effets, accordeur, ampli et instruments", "effets, accordeur et instruments")
    texte = texte.replace("avec les sept plugins Mastersuite", "avec les dix plugins Mastersuite")
    return texte


def main():
    contenu = json.loads(CHEMIN.read_text(encoding="utf-8"))
    avant = json.dumps(contenu, ensure_ascii=False, sort_keys=True)

    liste = contenu.setdefault("plugins", {}).get("liste", [])
    contenu["plugins"]["liste"] = [p for p in liste if p.get("nom") not in RETIRES]

    for section in ("site", "accueil", "promesses", "console", "plugins", "telechargement"):
        bloc = contenu.get(section, {})
        for cle, valeur in list(bloc.items()):
            if isinstance(valeur, str):
                bloc[cle] = dix(valeur)
            elif isinstance(valeur, list):
                bloc[cle] = [dix(v) if isinstance(v, str) else v for v in valeur]
    for carte in contenu.get("promesses", {}).get("cartes", []):
        if carte.get("titre") == "Masteriser":
            carte["texte"] = CARTE_MASTERISER
        else:
            carte["texte"] = dix(carte.get("texte", ""))

    apres = json.dumps(contenu, ensure_ascii=False, sort_keys=True)
    if avant == apres:
        print("content.json déjà à dix plugins, rien à faire")
        return 0

    sauvegarde = DATA / "backups" / time.strftime("content-%Y%m%d-%H%M%S-avant-dix-plugins.json")
    sauvegarde.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CHEMIN, sauvegarde)
    temporaire = CHEMIN.with_suffix(".json.tmp")
    temporaire.write_text(json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")
    st = CHEMIN.stat()
    os.chown(temporaire, st.st_uid, st.st_gid)
    os.chmod(temporaire, st.st_mode & 0o777)
    os.replace(temporaire, CHEMIN)
    print("content.json mis à jour : %d plugins (sauvegarde %s)" % (len(contenu["plugins"]["liste"]), sauvegarde.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
