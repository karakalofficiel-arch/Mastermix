#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Configure and build MasterMix under MSYS2 MINGW64.
#   tools/mastermix/build.sh            # configure (if needed) + build
#   tools/mastermix/build.sh configure  # force reconfigure
#   tools/mastermix/build.sh clean
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ "${MSYSTEM:-}" != "MINGW64" ]; then
	echo "error: run this from an MSYS2 MINGW64 shell" >&2
	exit 1
fi

export PYTHON=/mingw64/bin/python3
JOBS="${JOBS:-$(nproc)}"

CONFIGURE_FLAGS=(
	# waf probes MSVC first on win32 when Visual Studio is installed; force MinGW
	--check-c-compiler=gcc
	--check-cxx-compiler=g++
	--program-name=MasterMix
	--dist-target=mingw
	--with-backends=portaudio,dummy,jack
	--optimize
	--no-lrdf
	--no-dr-mingw
	--cxx17
	--no-phone-home
	--prefix=/mingw64
)

# PortAudio with ASIO (built by tools/mastermix/build-portaudio-asio.sh) takes
# precedence over the MSYS2 package when present.
DEPS_PREFIX=$PWD/build/deps/prefix
if [ -f "$DEPS_PREFIX/include/pa_asio.h" ]; then
	echo "using PortAudio+ASIO from $DEPS_PREFIX"
	export PKG_CONFIG_PATH="$DEPS_PREFIX/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
	export LINKFLAGS="-L$DEPS_PREFIX/lib ${LINKFLAGS:-}"
	CONFIGURE_FLAGS+=(--also-include="$DEPS_PREFIX/include" --also-libdir="$DEPS_PREFIX/lib")
fi

case "${1:-build}" in
	clean)
		$PYTHON ./waf clean
		exit 0
		;;
	configure)
		$PYTHON ./waf configure "${CONFIGURE_FLAGS[@]}"
		;;
	build)
		# reconfigure when never configured, or when the waf lock points at
		# another output dir (e.g. after a --out=build-tests test build)
		if [ ! -f build/c4che/_cache.py ] || ! grep -q "out_dir = '$(cygpath -m "$PWD")/build'" .lock-waf_win32_build 2>/dev/null; then
			$PYTHON ./waf configure "${CONFIGURE_FLAGS[@]}"
		fi
		;;
	*)
		echo "usage: $0 [build|configure|clean]" >&2
		exit 2
		;;
esac

$PYTHON ./waf build -j"$JOBS"
echo "--- built:"
ls -la build/gtk2_ardour/*.exe
