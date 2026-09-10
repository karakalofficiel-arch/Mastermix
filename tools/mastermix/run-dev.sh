#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Launch the freshly built MasterMix from the build tree (MSYS2 MINGW64).
# Ardour's own ardev-win sets every *_PATH variable for in-tree resources
# (themes, splash, backends, surfaces) and prepends the DLL directories.
set -euo pipefail
cd "$(dirname "$0")/../.."
[ -f build/gtk2_ardour/ardev_common_waf.sh ] || { echo "build first: tools/mastermix/build.sh" >&2; exit 1; }
exec gtk2_ardour/ardev-win "$@"
