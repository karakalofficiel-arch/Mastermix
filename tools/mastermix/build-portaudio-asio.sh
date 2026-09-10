#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Build a static PortAudio with ASIO support for the MasterMix PortAudio
# backend. MSYS2's PortAudio package has WASAPI/WDM-KS/DirectSound/MME but no
# ASIO (the Steinberg ASIO SDK is proprietary and cannot be redistributed as
# source, but binaries built with it may be distributed).
#
# Output: build/deps/prefix/{include/pa_asio.h, lib/libportaudio.a,
#         lib/pkgconfig/portaudio-2.0.pc}. tools/mastermix/build.sh picks
#         that prefix up automatically when it exists.
set -euo pipefail
cd "$(dirname "$0")/../.."
[ "${MSYSTEM:-}" = "MINGW64" ] || { echo "run from MINGW64" >&2; exit 1; }

DEPS=$PWD/build/deps
PREFIX=$DEPS/prefix
PA_VERSION=${PA_VERSION:-v19.7.0}
ASIOSDK_URL=${ASIOSDK_URL:-https://download.steinberg.net/sdk_downloads/asiosdk_2.3.3_2019-06-14.zip}
mkdir -p "$DEPS"

# 1. ASIO SDK (accepting Steinberg's licence is the builder's responsibility)
if ! ls -d "$DEPS"/asiosdk_*/common >/dev/null 2>&1; then
	[ -f "$DEPS/asiosdk.zip" ] || curl -L -o "$DEPS/asiosdk.zip" "$ASIOSDK_URL"
	(cd "$DEPS" && unzip -q -o asiosdk.zip)
fi
ASIOSDK=$(ls -d "$DEPS"/asiosdk_*/ | head -1)
ASIOSDK=${ASIOSDK%/}
echo "ASIO SDK: $ASIOSDK"

# 2. PortAudio sources
if [ ! -d "$DEPS/portaudio-src" ]; then
	git clone --depth 1 --branch "$PA_VERSION" https://github.com/PortAudio/portaudio.git "$DEPS/portaudio-src"
fi

# 3. configure + build (static, every Windows host API incl. ASIO)
rm -rf "$DEPS/portaudio-build"
cmake -S "$DEPS/portaudio-src" -B "$DEPS/portaudio-build" -G Ninja \
	-DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
	-DCMAKE_INSTALL_PREFIX="$PREFIX" \
	-DASIOSDK_ROOT_DIR="$ASIOSDK" \
	-DPA_USE_ASIO=ON -DPA_USE_WASAPI=ON -DPA_USE_WDMKS=ON -DPA_USE_DS=ON -DPA_USE_WMME=ON \
	-DPA_BUILD_STATIC=ON -DPA_BUILD_SHARED=OFF -DPA_BUILD_TESTS=OFF -DPA_BUILD_EXAMPLES=OFF
cmake --build "$DEPS/portaudio-build" --parallel
cmake --install "$DEPS/portaudio-build"

# 4. sanity check
[ -f "$PREFIX/include/pa_asio.h" ] || { echo "pa_asio.h missing: ASIO not enabled" >&2; exit 1; }
if ! nm "$PREFIX/lib/libportaudio.a" 2>/dev/null | grep -q PaAsio_ShowControlPanel; then
	echo "libportaudio.a has no ASIO symbols" >&2; exit 1
fi
echo "PortAudio with ASIO installed in $PREFIX"
ls "$PREFIX/include" | tr '\n' ' '; echo
