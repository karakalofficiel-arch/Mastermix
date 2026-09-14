# Copyright (C) 2026 Ahmed Hadjadj
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""Apply the Pro Tools French vocabulary to Ardour's fr.po files.

Usage:  python tools/mastermix/po-protools.py
Rewrites gtk2_ardour/po/fr.po and libs/ardour/po/fr.po in place (idempotent,
rerun after an upstream rebase), then checks them with msgfmt when available.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# msgid -> new msgstr, per file. Only strings visible in the Edit/Mix windows.
SUBSTITUTIONS = {
    "gtk2_ardour/po/fr.po": {
        "Editor": "Édition",
        "Mixer": "Mixage",
        "Regions": "Clips",
        "Region": "Clip",
        "Bars:Beats": "Mesures|Temps",
        "Tracks & Busses": "Pistes",
        "Track & Bus Groups": "Groupes",
        "Show Sends": "Afficher les départs",
        "Send": "Départ",
        "Nudge": "Déplacer",
        "Snap": "Grille",
        "Slide": "Slip",
        "Ripple": "Shuffle",
        "EditMode|Lock": "Spot",
    },
    "libs/ardour/po/fr.po": {
        "Send": "Départ",
        "Slide": "Slip",
        "Ripple": "Shuffle",
    },
}

# Strings introduced by MasterMix (must match the _() literals in the C++).
ADDITIONS = {
    "gtk2_ardour/po/fr.po": {
        "INSERTS A-E": "INSERTS A-E",
        "SENDS A-E": "DÉPARTS A-E",
        "I/O": "E/S",
        "Click to add a plugin": "Cliquer pour ajouter un plugin",
        "Click to add a send": "Cliquer pour ajouter un départ",
        "%1 (+%2 more inserts, see the mixer)": "%1 (+%2 inserts, voir le mixage)",
        "%1 (pre-fader)": "%1 (pré-fader)",
        "Fader gain (scroll to change)": "Gain du fader (molette pour modifier)",
        "Pan (click to open the panner)": "Pan (cliquer pour ouvrir le panoramique)",
        "Bypass": "Contourner",
        "Activate": "Activer",
        "Remove": "Retirer",
        "Add plugin...": "Ajouter un plugin…",
        "Remove send": "Retirer le départ",
        "(no bus available)": "(aucun bus disponible)",
        "Pan: %1": "Pan : %1",
        "Send: %1 (%2)": "Départ : %1 (%2)",
        "SHUFFLE": "SHUFFLE",
        "SPOT": "SPOT",
        "SLIP": "SLIP",
        "GRID": "GRID",
        "Start": "Début",
        "End": "Fin",
        "Length": "Longueur",
        "Pro Tools layout for the Edit window (restart required)":
            "Disposition Pro Tools de la fenêtre Édition (redémarrage requis)",
    },
}

_ENTRY = re.compile(r'^msgid "(?P<id>.*)"(?P<nl>\r?\n)msgstr "(?P<str>.*)"(?=\r?\n|$)', re.M)


def apply(text, table, additions):
    """Return text with msgstr replaced for listed msgids and additions appended.

    The header entry (empty msgid) is never touched. Additions already present
    in the file are updated in place, missing ones are appended once.
    """
    nl = "\r\n" if "\r\n" in text else "\n"
    replacements = {k: v for k, v in table.items() if k}
    replacements.update({k: v for k, v in additions.items() if k})

    def repl(m):
        new = replacements.get(m.group("id"))
        if new is None:
            return m.group(0)
        return f'msgid "{m.group("id")}"{m.group("nl")}msgstr "{new}"'

    text = _ENTRY.sub(repl, text)

    present = set(m.group("id") for m in _ENTRY.finditer(text))
    extra = [
        f'{nl}#: mastermix{nl}msgid "{k}"{nl}msgstr "{v}"{nl}'
        for k, v in additions.items() if k and k not in present
    ]
    if extra:
        if not text.endswith(nl):
            text += nl
        text += "".join(extra)
    return text


def main():
    ok = True
    for rel in sorted(set(SUBSTITUTIONS) | set(ADDITIONS)):
        path = ROOT / rel
        text = path.read_bytes().decode("utf-8")
        # the repository stores the .po files with LF endings
        new = apply(text, SUBSTITUTIONS.get(rel, {}), ADDITIONS.get(rel, {})).replace("\r\n", "\n")
        if new != text:
            path.write_bytes(new.encode("utf-8"))
            print(f"updated {rel}")
        else:
            print(f"unchanged {rel}")
        msgfmt = shutil.which("msgfmt") or r"C:\msys64\usr\bin\msgfmt.exe"
        if Path(msgfmt).exists():
            r = subprocess.run([msgfmt, "--check", "-o", "-", str(path)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode != 0:
                ok = False
                print(r.stderr, file=sys.stderr)
        else:
            print("msgfmt not found, syntax not checked", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
