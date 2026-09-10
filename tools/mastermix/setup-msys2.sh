#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Install every package MasterMix needs to build under MSYS2 MINGW64.
# Run from a MINGW64 shell (or via
#   MSYSTEM=MINGW64 /c/msys64/usr/bin/bash.exe -lc tools/mastermix/setup-msys2.sh).
set -euo pipefail

if [ "${MSYSTEM:-}" != "MINGW64" ]; then
	echo "error: run this from an MSYS2 MINGW64 shell (MSYSTEM=${MSYSTEM:-unset})" >&2
	exit 1
fi

P=mingw-w64-x86_64

MSYS_PKGS=(base-devel git)

MINGW_PKGS=(
	$P-gcc $P-binutils $P-make $P-gdb $P-pkgconf $P-cmake $P-ninja $P-python $P-ntldd $P-nsis
	$P-boost $P-glib2 $P-glibmm $P-libsigc++ $P-libxml2
	$P-cairo $P-cairomm $P-pango $P-pangomm $P-fontconfig $P-libpng $P-gdk-pixbuf2
	$P-libsndfile $P-flac $P-libogg $P-libsamplerate $P-soundtouch $P-rubberband $P-aubio $P-fftw
	$P-curl $P-libarchive $P-liblo $P-taglib $P-libusb $P-libwebsockets
	$P-lv2 $P-lilv $P-serd $P-sord $P-sratom
	$P-vamp-plugin-sdk $P-cppunit $P-portaudio $P-jack2 $P-readline
)

pacman -Sy --noconfirm
pacman -S --needed --noconfirm "${MSYS_PKGS[@]}"
pacman -S --needed --noconfirm "${MINGW_PKGS[@]}"

echo "--- pkg-config check"
MODULES="glib-2.0 gthread-2.0 glibmm-2.4 giomm-2.4 sigc++-2.0 cairomm-1.0 pangomm-1.4 pangocairo
sndfile samplerate rubberband aubio fftw3f libcurl libarchive liblo taglib libusb-1.0
lv2 lilv-0 serd-0 sord-0 sratom-0 vamp-sdk vamp-hostsdk cppunit portaudio-2.0 jack libwebsockets libxml-2.0"
missing=0
for m in $MODULES; do
	if pkg-config --exists "$m"; then
		printf '  ok   %s %s\n' "$m" "$(pkg-config --modversion "$m")"
	else
		printf '  MISS %s\n' "$m"; missing=1
	fi
done
exit $missing
