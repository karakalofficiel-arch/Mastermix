#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Stage a relocatable MasterMix tree from the MSYS2 build and wrap it in an
# NSIS installer. Run after tools/mastermix/build.sh, from MINGW64.
#
# Layout mirrors tools/x-win/package.sh (the official Ardour Windows
# package): bin/ holds the exe and every DLL, lib/<ardour9>/ the backends,
# surfaces, panners and bundled LV2 plugins, share/<ardour9>/ the data
# (themes, resources, locale, scripts, ...).
set -euo pipefail
cd "$(dirname "$0")/../.."
[ "${MSYSTEM:-}" = "MINGW64" ] || { echo "run from MINGW64" >&2; exit 1; }

PYTHON=/mingw64/bin/python3
PRODUCT=MasterMix
VERSION=$(sed -n "s/^VERSION = '\(.*\)'/\1/p" build/c4che/_cache.py | head -1)
VERSION=${VERSION:-9.8}
LOWER=$(sed -n "s/^lwrcase_dirname = '\(.*\)'/\1/p" build/c4che/_cache.py | head -1)
LOWER=${LOWER:-ardour9}
STAGE=build/stage
PREFIX=$STAGE/msys64/mingw64        # --prefix=/mingw64 mapped under --destdir
DEST=dist/$PRODUCT

# 1. compile translations and install everything into the staging prefix
$PYTHON ./waf i18n_mo
rm -rf "$STAGE"
$PYTHON ./waf install --destdir="$PWD/$STAGE"
[ -d "$PREFIX/lib/$LOWER" ] || { echo "staging failed: $PREFIX/lib/$LOWER missing" >&2; exit 1; }

# 2. assemble the package tree
rm -rf "$DEST"
mkdir -p "$DEST/bin" "$DEST/lib/$LOWER" "$DEST/share"

EXE=$(ls "$PREFIX/lib/$LOWER"/ardour-*.exe | head -1)
cp "$EXE" "$DEST/bin/$PRODUCT.exe"
cp "$PREFIX/lib/$LOWER"/*.dll "$DEST/bin/"
cp "$PREFIX/lib/$LOWER"/*.exe "$DEST/bin/" 2>/dev/null || true
rm -f "$DEST/bin"/ardour-*.exe
cp "$PREFIX/bin"/*.exe "$DEST/bin/" 2>/dev/null || true

for sub in backends engines surfaces panners LV2 vamp; do
	[ -d "$PREFIX/lib/$LOWER/$sub" ] && cp -r "$PREFIX/lib/$LOWER/$sub" "$DEST/lib/$LOWER/"
done
# plugin DLLs must not carry import libraries
find "$DEST/lib" -name '*.dll.a' -delete

cp -r "$PREFIX/share/$LOWER" "$DEST/share/"
[ -d "$PREFIX/etc/$LOWER" ] && cp -r "$PREFIX/etc/$LOWER"/* "$DEST/share/$LOWER/"
rm -f "$DEST/share/$LOWER/themes/"*-ardour.colors
cp COPYING "$DEST/share/"
cp gtk2_ardour/icons/${PRODUCT}.ico "$DEST/share/"
# square cursors without hotspot file, as upstream does for Windows
cp gtk2_ardour/icons/cursor_square/*.png "$DEST/share/$LOWER/icons/" 2>/dev/null || true

# 3. MinGW runtime DLLs the exes (MasterMix, ardour9-lua, session utils), libs and plugins depend on
ntldd -R "$DEST"/bin/*.exe "$DEST"/bin/*.dll "$DEST/lib/$LOWER"/*/*.dll 2>/dev/null \
	| grep -io '[a-z]:.msys64.mingw64.bin.[^ ]*\.dll' | sort -u | while read -r dll; do
		cp -n "$(cygpath -u "$dll")" "$DEST/bin/" 2>/dev/null || true
	done

# 4. GTK/pango runtime data (pixbuf loaders, fontconfig)
mkdir -p "$DEST/lib/gdk-pixbuf-2.0" "$DEST/etc/fonts"
cp -r /mingw64/lib/gdk-pixbuf-2.0/* "$DEST/lib/gdk-pixbuf-2.0/" 2>/dev/null || true
cp -r /mingw64/etc/fonts/* "$DEST/etc/fonts/" 2>/dev/null || true

# 5. installer
mkdir -p dist
sed -e "s|@VERSION@|$VERSION|g" -e "s|@DEST@|$(cygpath -m "$PWD/$DEST")|g" -e "s|@LOWER@|$LOWER|g" \
	tools/mastermix/mastermix.nsi.in > dist/mastermix.nsi
makensis -V2 dist/mastermix.nsi
du -sh "$DEST"
ls -la dist/*.exe
