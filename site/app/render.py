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
        "description": "MasterMix 2 est une station de travail audio professionnelle et facile pour Windows : enregistrez, mixez et masterisez dans une seule fenêtre, en français, avec les sept plugins Mastersuite inclus. Licence à vie offerte aux 100 premiers utilisateurs, 10 € ensuite.",
        "contact": "contact@mastermix.fr",
    },
    "accueil": {
        "surtitre": "Station de travail audio pour Windows",
        "titre": "MasterMix",
        "accroche": "La station de travail audio professionnelle, *facile*, pour mixer et masteriser.",
        "bouton": "Télécharger pour Windows",
        "meta": "Version 2.19 · Windows 10 / 11, 64 bits · Licence à vie offerte aux 100 premiers utilisateurs, 10 € ensuite",
        "capture": "editeur.jpg",
        "capture_alt": "Fenêtre d'édition de MasterMix : pistes, inserts, départs et entrées-sorties",
        "legende": "Fenêtre d'édition : chaque piste affiche ses inserts, ses départs et ses entrées-sorties.",
    },
    "promesses": {
        "titre": "Facile à prendre en main, sérieuse jusqu'au master.",
        "sous_titre": "Tout ce qu'il faut pour enregistrer, mixer et masteriser, dans une seule fenêtre lisible, en français.",
        "cartes": [
            {"titre": "Facile", "texte": "Une disposition inspirée des grandes consoles : inserts, départs et entrées-sorties directement dans l'en-tête de chaque piste. Modes SHUFFLE, SPOT, SLIP et GRID, horloges Début / Fin / Longueur. Interface entièrement en français."},
            {"titre": "Mixer", "texte": "Une tranche par piste, bus et retours, gel des pistes en un raccourci. Vos instruments et effets VST3, VST2 et CLAP, repérés automatiquement et hébergés dans un processus séparé. Pilotes ASIO pour une latence minimale."},
            {"titre": "Masteriser", "texte": "Les treize plugins Mastersuite sont inclus : égaliseur MasterQ, compresseur MasterComp 76, limiteur true-peak MasterL, restauration MasterClean, assistant de mastering MasterFlem, réverbe MasteRev, délai MasterDelay, accordeur MasterTune, ampli MasterBend, et quatre instruments : batterie MasterDrum, piano MasterKeys, cordes MasterString et basse MasterBass."},
        ],
    },
    "console": {
        "surtitre": "La console",
        "titre": "Une tranche par piste, tout sous les yeux.",
        "texte": "Inserts, départs, panoramique, fader et vumètre alignés sur chaque tranche. Les instruments multi-sorties tiennent sur une seule tranche, ou une par sortie si vous le demandez. Le master reste à droite, toujours visible.",
        "capture": "mixer.jpg",
        "capture_alt": "Console de mixage de MasterMix",
        "points": [
            "Bus, retours et départs auxiliaires",
            "Gel des pistes gourmandes, rendu audible immédiatement",
            "Mastersuite : treize plugins inclus, effets, accordeur, ampli et instruments",
        ],
    },
    "plugins": {
        "surtitre": "Mastersuite",
        "titre": "Treize plugins inclus, du premier accord au master.",
        "texte": "Tous en VST3, habillage MasterMix, installés avec la station. Ils fonctionnent aussi dans tout autre hôte VST3 64 bits.",
        "liste": [
            {"nom": "MasterQ", "role": "Égaliseur", "capture": "plugins/masterq.jpg", "texte": "Égaliseur paramétrique 16 bandes : courbe interactive à la souris, analyseur de spectre en temps réel, cloches, plateaux, coupe-bas et coupe-haut. Pour sculpter une piste ou corriger un master."},
            {"nom": "MasterComp 76", "role": "Compresseur", "capture": "plugins/mastercomp76.jpg", "texte": "Compresseur FET inspiré du 1176, une seule rangée de commandes : entrée, sortie, attaque, relâchement, ratios 4 / 8 / 12 / 20 et mode « tous enfoncés ». Circuit transistor ou lampe. Voix, batterie, basse."},
            {"nom": "MasterL", "role": "Limiteur", "capture": "plugins/masterl.jpg", "texte": "Limiteur true-peak pour le master : plafond, gain d'entrée, relâchement, mesure de loudness (LUFS) et de crête vraie intégrée. Ce qui sort ne dépasse jamais le plafond, quelle que soit la plateforme."},
            {"nom": "MasterClean", "role": "Restauration", "capture": "plugins/masterclean.jpg", "texte": "Restauration audio : réduction de bruit large bande, suppression de ronflette 50 / 60 Hz et de ses harmoniques. Pour rattraper une prise bruyante ou un enregistrement ancien."},
            {"nom": "MasterFlem", "role": "Assistant de mastering", "capture": "plugins/masterflem.jpg", "texte": "Assistant de mastering : analyse le mix, vise une cible (streaming, club, radio) et règle sa chaîne égaliseur, compresseur et limiteur pour l'atteindre. Comparaison A/B, réglages modifiables à la main."},
            {"nom": "MasteRev", "role": "Réverbe", "capture": "plugins/masterev.jpg", "texte": "Réverbe algorithmique à réseau de huit lignes : taille, pré-délai, amortissement, largeur, mix. Douze préconfigurations voix et instruments qui sonnent juste dès le choix, en insert ou sur un bus."},
            {"nom": "MasterDelay", "role": "Délai", "capture": "plugins/masterdelay.jpg", "texte": "Délai stéréo synchronisé au tempo ou libre, ping-pong, retour filtré et saturé en douceur, modulation type bande. Douze préconfigurations : slapback, doublage, écho pointé, dub."},
            {"nom": "MasterTune", "role": "Accordeur", "capture": "plugins/mastertune.jpg", "texte": "Accordeur chromatique à poser sur la piste : note, écart en cents sur une aiguille, fréquence mesurée, La de référence réglable, notation C D E ou Do Ré Mi, sortie muette pendant l'accordage. Précis au cent."},
            {"nom": "MasterBend", "role": "Ampli", "capture": "plugins/masterbend.jpg", "texte": "Simulation d'ampli guitare et basse à brancher sur une piste DI : cinq modèles (clean US, crunch UK, lead, boutique, basse), quatre baffles (ou aucun, pour une réponse impulsionnelle externe), égalisation basses / médiums / aigus / présence, porte de bruit. Dix préréglages."},
            {"nom": "MasterDrum", "role": "Batterie", "capture": "plugins/masterdrum.jpg", "texte": "Batterie à échantillons : kit dessiné en 3D qui s'allume à chaque coup, patterns MIDI joués au tempo de la session, morceau enchaîné section par section, micros proche / overheads / room. Glissez le morceau vers une piste de MasterMix. Vos WAV ou SFZ, ou les sons internes."},
            {"nom": "MasterKeys", "role": "Piano", "capture": "plugins/masterkeys.jpg", "texte": "Piano à échantillons : le Salamander Grand Piano (Yamaha C5, 16 couches de vélocité, Alexander Holm, CC-BY 3.0) inclus dans l'installeur. Grille d'accords : tonalité, « 4 accords » par style, suggestions, accompagnement calé sur la lecture et glissé en MIDI."},
            {"nom": "MasterString", "role": "Violon et violoncelle", "capture": "plugins/masterstring.jpg", "texte": "Violon et violoncelle : six articulations par keyswitches (arco, pizzicato, staccato, trémolo, sourdine, col legno), legato et portamento en mode MONO, manches affichés. Grille d'accords partagée avec MasterKeys et MasterBass. Vos WAV ou SFZ, ou les sons internes."},
            {"nom": "MasterBass", "role": "Basse", "capture": "plugins/masterbass.jpg", "texte": "Basse à échantillons : les deux basses cinq cordes Black And Blue (Karoryfer Samples, CC0) incluses dans l'installeur, huit articulations par keyswitches (doigt, médiator, étouffé, slap, pop, harmonique, ghost, glissé), manche, legato et portamento, accompagnement qui suit la grille d'accords. Vos WAV ou SFZ en priorité."},
        ],
    },
    "telechargement": {
        "titre": "Télécharger MasterMix 2.19",
        "texte": "Installeur pour Windows 10 et 11, 64 bits, avec les treize plugins VST3 Mastersuite et, au choix, les banques de sons embarquées : le piano Salamander pour MasterKeys et les basses Black And Blue pour MasterBass. Aucun téléchargement pendant l'installation. Licence à vie offerte aux 100 premiers utilisateurs, 10 € ensuite. Sans compte ni abonnement ; MasterMix vous propose lui-même les mises à jour suivantes.",
        "fichier": "MasterMix-2.19-Setup-x64.exe",
        "taille": 1284097038,
        "sha256": "4e329193b301894d60f1994dfa95fdbde184137402a07d3b06dee4d2af6d653e",
        "note": "Au premier lancement, Windows SmartScreen peut afficher un avertissement : l'installeur n'est pas signé par un certificat commercial. Vérifiez l'empreinte, puis choisissez « Informations complémentaires » › « Exécuter quand même ».",
    },
    "configuration": {
        "titre": "Configuration requise",
        "texte": "Un PC récent suffit. Une interface audio avec pilote ASIO donne le meilleur résultat.",
        "lignes": [
            ["Système", "Windows 10 ou 11, 64 bits"],
            ["Processeur", "x86-64, 4 cœurs recommandés"],
            ["Mémoire", "8 Go recommandés"],
            ["Espace disque", "200 Mo, plus vos sessions"],
            ["Audio", "ASIO recommandé ; WASAPI pris en charge"],
            ["Greffons", "VST3, VST2 et CLAP, 64 bits"],
        ],
    },
    "pied": {
        "signature": "· mastermix.fr · Ahmed Hadjadj, 2026",
        "licence": "Logiciel propriétaire, © 2026 Ahmed Hadjadj, tous droits réservés. MasterMix 2 est construit sur Futureboard Studio, © 2026 Ariz Kamizuki, sous licence MIT, sans affiliation avec ce projet. ASIO et VST sont des marques de Steinberg Media Technologies GmbH.",
    },
}

# Champs texte modifiables depuis l'admin, par section (ordre d'affichage).
CHAMPS = {
    "site": ["titre", "titre_page", "description", "contact"],
    "accueil": ["surtitre", "titre", "accroche", "bouton", "meta", "capture", "capture_alt", "legende"],
    "promesses": ["titre", "sous_titre", "cartes"],
    "console": ["surtitre", "titre", "texte", "capture", "capture_alt", "points"],
    "plugins": ["surtitre", "titre", "texte", "liste"],
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
    v["plugins.liste"] = "".join(
        '      <div class="plug"><div class="shot"><img src="%s" alt="%s" loading="lazy"></div>'
        '<h3>%s<span>%s</span></h3><p>%s</p></div>\n'
        % (e(p.get("capture", "")), e(p.get("nom", "")), e(p.get("nom", "")), e(p.get("role", "")), e(p.get("texte", "")))
        for p in c.get("plugins", {}).get("liste", [])
    )
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
