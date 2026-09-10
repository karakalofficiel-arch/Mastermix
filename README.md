# MasterMix

MasterMix est une station audionumérique (DAW) pour Windows, dérivée
d'[Ardour](https://ardour.org/) 9.8. Elle conserve l'intégralité des
fonctions d'Ardour avec une identité visuelle vert pomme et noir.

Auteur : Ahmed Hadjadj — 2026.
Licence : GNU GPL version 2 ou ultérieure (voir `COPYING`).
Ardour est © 1999-2026 Paul Davis et contributeurs. « Ardour » est une
marque de Paul Davis ; MasterMix n'est pas affilié au projet Ardour.

## Construire sous Windows (MSYS2 MINGW64)

1. Installer MSYS2 (https://www.msys2.org/) dans `C:\msys64`.
2. Depuis un shell MINGW64, à la racine du dépôt :
   ```
   tools/mastermix/setup-msys2.sh   # installe les dépendances
   tools/mastermix/build.sh          # configure + compile
   tools/mastermix/package-msys2.sh  # produit l'installeur NSIS
   ```
3. Le binaire est dans `build/gtk2_ardour/`, l'installeur dans `dist/`.

## Identité visuelle

Logo, icônes, splash et thème sont générés par les scripts de
`mastermix-branding/` (`python mastermix-branding/render.py`,
`python mastermix-branding/palette.py`).

## Dépôt

Branche `mastermix`, basée sur le tag Ardour `9.8`. Remote `upstream`
= https://github.com/Ardour/ardour.git. Les modifications MasterMix sont
des commits par-dessus le tag, pour rebaser sur les versions futures.
