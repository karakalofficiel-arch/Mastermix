# MasterMix — Phase 1 : fork Ardour 9.8, rebranding, thème vert pomme / noir, build Windows

Auteur : Ahmed Hadjadj
Date : 2026-09-10
Statut : validé

## 1. Objectif

MasterMix est un DAW Windows dérivé d'Ardour 9.8. La phase 1 livre un
binaire Windows 64 bits qui possède **toutes les fonctions d'Ardour 9.8**,
sous le nom MasterMix, avec un thème vert pomme (`#A4DE02`) sur noir et un
logo dérivé de celui d'Ardour (un **M** à la place du **A**).

Aucune fonctionnalité nouvelle en phase 1. Aucune fonction retirée.

## 2. Contraintes

- **Licence** : Ardour est GPLv2+. MasterMix reste GPLv2+, code source public.
  Le fichier `COPYING` est conservé tel quel.
- **Marques** : « Ardour » et son logo sont des marques de Paul Davis. Tout
  élément visible par l'utilisateur (nom, logo, splash, icônes, installeur,
  À propos) est rebrandé. Les mentions « basé sur Ardour » restent dans le
  README et le dialogue À propos (attribution GPL).
- **Auteur** : tout nouveau fichier porte l'en-tête
  `Copyright (C) 2026 Ahmed Hadjadj` sous GPLv2+. Les commits git sont
  signés `Ahmed Hadjadj <karakalofficiel@gmail.com>`. L'éditeur (publisher)
  de l'installeur NSIS est « Ahmed Hadjadj ».
- **Compatibilité sessions** : les noms de nœuds XML `"Ardour"` dans les
  fichiers de session, de config (`rc_configuration.cc`,
  `session_configuration.cc`, `ui_config.cc`, `utils.cc`) et l'espace de
  noms Lua `Ardour` (`luaproc.cc`) **ne sont pas modifiés**. Ce sont des
  formats de fichier, pas du branding. MasterMix ouvre les sessions Ardour
  et inversement.
- **Toolchain** : MSYS2 MINGW64 natif sur Windows 11. Pas de MSVC.

## 3. Dépôt

- `A:\claude\mastermix` est un clone d'Ardour au tag `9.8`, remote
  `upstream = https://github.com/Ardour/ardour.git`, branche de travail
  `mastermix`.
- Toutes les modifications MasterMix sont des commits par-dessus `9.8`, en
  petits commits thématiques, pour rebaser sur les futures versions
  d'Ardour.
- Nouveaux répertoires :
  - `mastermix-branding/` : sources SVG du logo, script de rendu, palette.
  - `tools/mastermix/` : scripts de build MSYS2 et de packaging.
  - `docs/superpowers/` : specs et plans.
- `README.md` MasterMix ajouté à la racine (le `README` Ardour reste).

## 4. Rebranding par convention de nommage

Ardour intègre un mécanisme de produit dérivé (utilisé par Mixbus) :
l'option `./waf configure --program-name=MasterMix` définit
`PROGRAM_NAME="MasterMix"` et sélectionne les ressources par nom de fichier.
Aucun patch C++ pour le nom.

Fichiers à fournir :

| Chemin | Rôle |
|---|---|
| `gtk2_ardour/resources/MasterMix-splash.png` | splash 400×348 (même taille qu'Ardour) |
| `gtk2_ardour/resources/MasterMix-small-splash.png` | splash réduit 100×87 |
| `gtk2_ardour/resources/MasterMix-icon_{16,22,32,48,256,512}px.png` | icônes application |
| `gtk2_ardour/icons/MasterMix.ico` | icône exe Windows (16 à 256 px), référencée par `windows_icon.rc` généré par `create_resource_file` |
| `gtk2_ardour/themes/dark-mastermix.colors` | thème (voir §5) |

Modifications de code minimales :

- `gtk2_ardour/ui_config_vars.inc.h` : valeur par défaut de `color-file`
  (`"dark"`) **inchangée**. `UIConfiguration::color_file_name()` compose
  `<base>-<program_name minuscule>.colors`, donc `dark-mastermix.colors`
  est chargé automatiquement. Le glob d'installation
  `themes/*-mastermix.colors` ne livre que les thèmes MasterMix.
- `gtk2_ardour/about.cc` : ajouter une section « MasterMix par Ahmed
  Hadjadj, basé sur Ardour » dans le dialogue À propos.
- `tools/x-win/package.sh` : copié en `tools/mastermix/package-msys2.sh`,
  adapté : `PROGRAM_NAME=MasterMix`, `PRODUCT_NAME=MasterMix`,
  icône `MasterMix.ico`, textes NSIS (titre, lien manuel), publisher
  « Ahmed Hadjadj », chemins des DLL MSYS2 au lieu du cross-stack Linux.
  Le script original reste intact pour le rebase.

## 5. Thème `dark-mastermix.colors`

Dérivé de `dark-ardour.colors` (535 couleurs, XML `<Color name value>`).
Une seule source de vérité : `mastermix-branding/palette.py` génère le
fichier `.colors` à partir de `dark-ardour.colors` + un dictionnaire de
substitutions, pour que le thème soit régénérable après un rebase.

Palette :

| Rôle | Valeur |
|---|---|
| Accent vert pomme | `#A4DE02` |
| Accent foncé (hover/pressed) | `#7FAE00` |
| Accent clair (texte sur noir) | `#C6F04A` |
| Noir fond principal (`theme:bg`) | `#0A0A0A` |
| Fond pistes (`theme:bg1`, `neutral:background`) | `#141414` |
| Fond règles (`theme:bg2`, `neutral:backgroundest`) | `#000000` |
| Widgets / boutons (`widget:bg`) | `#1E1E1E` |
| Gris moyen (grilles, texte des règles, `neutral:midground`) | `#5A5A5A` |
| Texte principal | `#E8E8E8` |

Règles d'application :

- Sélection, boutons actifs, horloges, fader de processeur, curseur de
  souris, marqueurs, piste MIDI, bouton solo, meter clip-free : vert pomme.
- Tête de lecture : rouge conservé. Bouton et indicateur d'enregistrement :
  rouge conservé. Ces deux conventions DAW ne changent pas.
- Vumètres : dégradé `#3E5A00 → #A4DE02 → #C6F04A`, zone jaune conservée
  au-dessus de −6 dBFS, pic rouge conservé.
- Couleurs `gtk_*` (menus, dialogues, entrées) : fond `#0A0A0A`/`#1E1E1E`,
  texte `#E8E8E8`, sélection `#A4DE02` avec texte noir.
- Contraste : tout texte vert sur noir ≥ 7:1 (WCAG AAA). Texte noir sur
  vert pomme ≥ 12:1.

## 6. Logo

- Source : `mastermix-branding/logo.svg` (512×512, viewBox carré).
- Composition : carré noir `#0A0A0A` à coins arrondis (rayon 18 %). Un
  **M** vert pomme construit comme le **A** d'Ardour : deux jambes obliques
  épaisses, sommet plat, et la barre médiane remplacée par une forme
  d'onde (comme la barre du A d'Ardour). Le V central du M est fait par
  la forme d'onde qui descend au centre.
- Variantes : `logo-mono.svg` (M vert sur fond transparent, pour splash),
  `logo-black.svg` (M noir sur transparent, pour impression).
- Splash `MasterMix-splash.png` 400×348 : fond noir, logo centré, texte
  « MasterMix » en Ubuntu/DejaVu Sans Bold vert pomme, sous-titre
  « basé sur Ardour 9.8 » gris.
- Rendu : `mastermix-branding/render.py` (Python 3.12 + `cairosvg` +
  `Pillow`) produit tous les PNG, l'`.ico` multi-résolution (16, 32, 48,
  256) et les deux splashs. Idempotent, lancé à la main.

## 7. Build MSYS2

- `tools/mastermix/setup-msys2.sh` : installe les paquets `pacman`
  (`mingw-w64-x86_64-` : gcc, pkgconf, boost, glibmm, gtkmm (non requis,
  ytk interne), libsndfile, libsamplerate, lv2, lilv, serd, sord, sratom,
  suil, fftw, vamp-plugin-sdk, rubberband, aubio, libarchive, liblo,
  taglib, cppunit, portaudio, jack2, libxml2, curl, libusb, hidapi,
  libwebsockets, readline, python) + `base-devel git`.
- `tools/mastermix/build.sh` :
  ```
  ./waf configure --program-name=MasterMix --with-backends=portaudio,dummy,jack \
                  --optimize --prefix=/mingw64 --dist-target=mingw
  ./waf build -j$(nproc)
  ```
  Backends : PortAudio (WASAPI/ASIO via portaudio MSYS2, ASIO SDK non
  inclus donc WASAPI/WDM-KS), Dummy, JACK.
- Patches de build éventuels : un fichier par patch dans
  `tools/mastermix/patches/`, appliqués en commits distincts sur la branche.
- Sortie : `build/gtk2_ardour/mastermix-9.8.0.exe` (le nom du binaire
  suit `PROGRAM_NAME` en minuscules).
- Packaging : `tools/mastermix/package-msys2.sh` copie exe, DLL (via
  `ldd`), `share/`, thèmes, ressources dans `dist/MasterMix/`, puis NSIS
  (`makensis`, paquet MSYS2 `mingw-w64-x86_64-nsis`) produit
  `MasterMix-9.8-Setup-x64.exe`.

## 8. Vérification

1. `./waf build` termine sans erreur.
2. `mastermix-9.8.0.exe` se lance ; capture d'écran du splash, de
   l'éditeur, du mixer.
3. Titre de la fenêtre commence par « MasterMix ».
4. Dialogue À propos affiche MasterMix, Ahmed Hadjadj, mention Ardour.
5. Thème `dark-mastermix` chargé : fond noir, sélection vert pomme.
6. Icône `.ico` visible dans l'Explorateur et la barre des tâches.
7. Tests unitaires existants `libs/pbd/test` et `libs/ardour/test`
   compilent et passent (`./waf configure --test` + `--run-tests`), ou
   échec documenté s'ils ne compilent pas sous MinGW (état upstream).
8. Installeur NSIS s'installe et se désinstalle proprement.

## 9. Hors périmètre phase 1

- Nouvelles fonctions, réorganisation d'interface.
- Thème clair, autres variantes de couleurs.
- Signature Authenticode du binaire (certificat requis).
- Site web, mises à jour automatiques, télémétrie.
- Support ASIO natif (SDK Steinberg propriétaire).
- Build 32 bits, macOS, Linux.
