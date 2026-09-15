"""Rendu HTML de la page publique et des pages libres à partir du contenu.

Le gabarit (gabarit.html) est la page validée le 2026-09-15, où chaque texte est
remplacé par un jeton @@section.champ@@. CONTENU_DEFAUT reproduit cette page à
l'identique : c'est le contenu importé au premier démarrage.
"""
import html
import re
from pathlib import Path

from app import markdown_lite

GABARIT = (Path(__file__).parent / "gabarit.html").read_text(encoding="utf-8")
_JETON = re.compile(r"@@([a-z_.0-9]+)@@")
_EM = re.compile(r"\*([^*]+)\*")

CONTENU_DEFAUT = {
    "site": {
        "titre": "MasterMix",
        "titre_page": "MasterMix — la station de travail audio professionnelle, facile, pour mixer et masteriser",
        "description": "MasterMix est une station de travail audio professionnelle et facile pour Windows : enregistrez, mixez et masterisez dans une seule fenêtre, en français. Gratuite.",
        "contact": "contact@mastermix.fr",
    },
    "accueil": {
        "surtitre": "Station de travail audio pour Windows",
        "titre": "MasterMix",
        "accroche": "La station de travail audio professionnelle, *facile*, pour mixer et masteriser.",
        "bouton": "Télécharger pour Windows",
        "meta": "Gratuit · Version 9.8.24 · Windows 10 / 11, 64 bits",
        "capture": "editeur.jpg",
        "capture_alt": "Fenêtre d'édition de MasterMix : pistes, inserts, départs et entrées-sorties",
        "legende": "Fenêtre d'édition : chaque piste affiche ses inserts, ses départs et ses entrées-sorties.",
    },
    "promesses": {
        "titre": "Facile à prendre en main, sérieuse jusqu'au master.",
        "sous_titre": "Tout ce qu'il faut pour enregistrer, mixer et masteriser, dans une seule fenêtre lisible, en français.",
        "cartes": [
            {"titre": "Facile", "texte": "Une disposition inspirée des grandes consoles : inserts, départs et entrées-sorties directement dans l'en-tête de chaque piste. Modes SHUFFLE, SPOT, SLIP et GRID. Interface entièrement en français."},
            {"titre": "Mixer", "texte": "Console complète : faders, départs, bus, VCA, automation, pistes illimitées. Vos instruments et effets VST3, VST2 et LV2, repérés automatiquement."},
            {"titre": "Masteriser", "texte": "Mesure de niveau et de loudness, montage non destructif, export multi-formats en un seul passage. Pilotes ASIO pour une latence minimale."},
        ],
    },
    "console": {
        "surtitre": "La console",
        "titre": "Une tranche par piste, tout sous les yeux.",
        "texte": "Greffons, départs, panoramique, fader et vumètre alignés sur chaque tranche. Huit scènes de mixage rappelables d'une touche. Le master reste à droite, toujours visible.",
        "capture": "mixer.jpg",
        "capture_alt": "Console de mixage de MasterMix",
        "points": [
            "Bus, VCA et départs auxiliaires illimités",
            "Automation de chaque paramètre, greffons compris",
            "Vumètres crête, RMS et loudness",
        ],
    },
    "telechargement": {
        "titre": "Télécharger MasterMix 9.8.24",
        "texte": "Installeur pour Windows 10 et 11, 64 bits. Gratuit, sans compte ni abonnement.",
        "fichier": "MasterMix-9.8.24-Setup-x64.exe",
        "taille": 68120243,
        "sha256": "c10463889c1534001ac940e48e7ab32199704b866b3d25f4f4e8ef8bf95135b1",
        "note": "Au premier lancement, Windows SmartScreen peut afficher un avertissement : l'installeur n'est pas signé par un certificat commercial. Vérifiez l'empreinte, puis choisissez « Informations complémentaires » › « Exécuter quand même ».",
    },
    "configuration": {
        "titre": "Configuration requise",
        "texte": "Un PC récent suffit. Une interface audio avec pilote ASIO donne le meilleur résultat.",
        "lignes": [
            ["Système", "Windows 10 ou 11, 64 bits"],
            ["Processeur", "x86-64, 4 cœurs recommandés"],
            ["Mémoire", "8 Go recommandés"],
            ["Espace disque", "400 Mo, plus vos sessions"],
            ["Audio", "ASIO recommandé ; WASAPI et MME pris en charge"],
            ["Greffons", "VST3, VST2 et LV2, 64 bits"],
        ],
    },
    "pied": {
        "signature": "· mastermix.fr · Ahmed Hadjadj, 2026",
        "licence": "Logiciel libre, licence GNU GPL version 2 ou ultérieure ; code source disponible sur demande. MasterMix est construit sur le moteur audio Ardour, © Paul Davis et contributeurs, sans affiliation avec ce projet ; « Ardour » est une marque de Paul Davis.",
    },
}

# Champs texte modifiables depuis l'admin, par section (ordre d'affichage).
CHAMPS = {
    "site": ["titre", "titre_page", "description", "contact"],
    "accueil": ["surtitre", "titre", "accroche", "bouton", "meta", "capture", "capture_alt", "legende"],
    "promesses": ["titre", "sous_titre", "cartes"],
    "console": ["surtitre", "titre", "texte", "capture", "capture_alt", "points"],
    "telechargement": ["titre", "texte", "fichier", "taille", "sha256", "note"],
    "configuration": ["titre", "texte", "lignes"],
    "pied": ["signature", "licence"],
}


def e(texte):
    """Échappe &, <, > et " ; garde l'apostrophe (attributs toujours entre guillemets doubles)."""
    return html.escape(str(texte if texte is not None else ""), quote=False).replace('"', "&quot;")


def format_taille(octets):
    try:
        octets = int(octets)
    except (TypeError, ValueError):
        return ""
    if octets >= 1024 * 1024:
        return "%d Mo" % round(octets / (1024 * 1024))
    if octets >= 1024:
        return "%d Ko" % round(octets / 1024)
    return "%d o" % octets


def _accroche(texte):
    return _EM.sub(r"<em>\1</em>", e(texte))


def _menu(pages):
    return "".join('    <a href="/p/%s">%s</a>\n' % (e(p["slug"]), e(p["titre"])) for p in pages if p.get("visible"))


def _valeurs(contenu, pages):
    c = contenu
    v = {}
    for section, champs in CHAMPS.items():
        for champ in champs:
            valeur = c.get(section, {}).get(champ, "")
            if isinstance(valeur, (str, int, float)):
                v["%s.%s" % (section, champ)] = e(valeur)
    v["accueil.accroche"] = _accroche(c.get("accueil", {}).get("accroche", ""))
    for i, carte in enumerate(c.get("promesses", {}).get("cartes", [])[:3]):
        v["promesses.cartes.%d.titre" % i] = e(carte.get("titre", ""))
        v["promesses.cartes.%d.texte" % i] = e(carte.get("texte", ""))
    v["console.points"] = "\n        ".join("<div>%s</div>" % e(p) for p in c.get("console", {}).get("points", []))
    v["configuration.lignes"] = "".join(
        "      <div><span>%s</span><span>%s</span></div>\n" % (e(l[0]), e(l[1]))
        for l in c.get("configuration", {}).get("lignes", []) if len(l) == 2
    )
    v["telechargement.taille_texte"] = e(format_taille(c.get("telechargement", {}).get("taille", 0)))
    v["menu"] = _menu(pages)
    return v


def page_accueil(contenu, pages=()):
    v = _valeurs(contenu, list(pages))
    return _JETON.sub(lambda m: v.get(m.group(1), ""), GABARIT)


_STYLE_PAGE = """<style>
.page{padding-top:64px;max-width:820px}
.page h1{font-size:clamp(32px,4vw,52px);line-height:1.1;letter-spacing:-.02em;color:var(--title);margin:0 0 24px}
.page h2{font-size:clamp(24px,2.6vw,32px);margin:40px 0 12px}
.page h3{font-size:20px;margin:28px 0 8px;color:var(--title)}
.page p,.page li{font-size:17px;color:var(--soft)}
.page ul{padding-left:22px}
.page img{border-radius:12px;border:1px solid var(--glow);margin:12px 0}
.page hr{border:0;border-top:1px solid var(--line);margin:32px 0}
.page code{font-family:Consolas,"Cascadia Mono",ui-monospace,monospace;background:var(--panel);padding:2px 6px;border-radius:4px;font-size:.9em}
</style>
"""


def page_libre(contenu, page, pages=()):
    """Page libre : même en-tête, même pied, corps Markdown."""
    accueil = page_accueil(contenu, pages)
    avant, _, reste = accueil.partition('<main class="wrap">')
    _, _, apres = reste.partition("</main>")
    titre_page = "%s — %s" % (page.get("titre", ""), contenu.get("site", {}).get("titre", ""))
    avant = re.sub(r"<title>.*?</title>", "<title>%s</title>" % e(titre_page), avant, count=1, flags=re.S)
    avant = avant.replace("</head>", _STYLE_PAGE + "</head>", 1)
    corps = '<main class="wrap page"><article>\n<h1>%s</h1>\n%s\n</article></main>' % (
        e(page.get("titre", "")), markdown_lite.rendre(page.get("contenu_md", "")))
    return avant + corps + apres
