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
"""Generate gtk2_ardour/themes/dark-mastermix.colors from Ardour's dark theme.

Usage:  python mastermix-branding/palette.py
Only the base colours listed in COLORS and the aliases in ALIASES change;
every other entry is copied verbatim so the file stays rebase-friendly.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "gtk2_ardour" / "themes" / "dark-ardour.colors"
TARGET = ROOT / "gtk2_ardour" / "themes" / "dark-mastermix.colors"

APPLE = "a4de02ff"
APPLE_DARK = "7fae00ff"
APPLE_LIGHT = "c6f04aff"
APPLE_DEEP = "4e7a00ff"
APPLE_DIM = "3e5a00ff"
APPLE_MID = "6b9400ff"
BLACK = "0a0a0aff"
NEAR_BLACK = "000000ff"
TRACK = "141414ff"
WIDGET = "1e1e1eff"
GREY_DARK = "2a2a2aff"
GREY_MID = "5a5a5aff"
TEXT = "e8e8e8ff"
TEXT_DIM = "c0c0c0ff"

# Base colour overrides. Keys are upstream names, values are RRGGBBAA.
COLORS = {
    # backgrounds
    "theme:bg": BLACK,                      # gtk background
    "theme:bg1": TRACK,                     # audio track
    "theme:bg2": NEAR_BLACK,                # ruler base, gtk_fg_selected
    "neutral:background": TRACK,
    "neutral:background2": GREY_DARK,
    "neutral:midground": GREY_MID,          # grid lines, ruler text
    "neutral:foreground": TEXT,
    "neutral:foreground2": TEXT_DIM,
    "widget:bg": WIDGET,                    # generic button
    "widget:gray": GREY_DARK,
    # accents
    "theme:contrasting clock": APPLE,       # clock text
    "theme:contrasting less": APPLE_DARK,   # markers, active transport buttons
    "theme:contrasting selection": APPLE,   # gtk_bg_selected
    "theme:contrasting alt": APPLE_LIGHT,   # delta clocks, clock edit cursor
    "widget:blue": APPLE_DARK,              # processor fader, knobs, panners
    "widget:blue lighter": APPLE,
    "widget:blue darker": "162000ff",       # audio bus
    "widget:green": APPLE_DEEP,             # post-fader, midi track
    "widget:green darker": "1e2a08ff",      # midi track base
    "alert:green": APPLE,                   # solo, contrasting indicator
    "alert:greenish": APPLE_DARK,
    # meters (yellow/orange/red segments stay upstream)
    "meter color0": APPLE_DIM,
    "meter color1": APPLE_MID,
    "meter color2": APPLE,
    "meter color3": APPLE_LIGHT,
}

# Alias overrides: selection-related items move from red to apple green.
ALIASES = {
    "gtk_track_header_selected": "theme:contrasting less",
    "selected region base": "theme:contrasting less",
    "selected time axis frame": "theme:contrasting selection",
    "selection": "theme:contrasting selection",
    "selection rect": "theme:contrasting selection",
}

# New colour entries appended to <Colors> (names that do not exist upstream).
# Phase 2: track header colours by type, Pro Tools style, kept dark so the
# apple-green selection and the #E8E8E8 text stay readable (>= 7:1).
EXTRA_COLORS = {
    "mastermix:audio track": "1c2733ff",   # blue-grey, audio track header
    "mastermix:midi track": "332a1cff",    # brown, MIDI / instrument header
    "mastermix:audio bus": "1f2e14ff",     # dark green, aux bus header
    "mastermix:master bus": "33141cff",    # dark wine, master header
}

# Aliases retargeted (existing upstream) or appended (new) in <ColorAliases>.
EXTRA_ALIASES = {
    "gtk_audio_track": "mastermix:audio track",
    "gtk_midi_track": "mastermix:midi track",
    "gtk_audio_bus": "mastermix:audio bus",
    "gtk_master_bus": "mastermix:master bus",
}

_COLOR_RE = re.compile(r'(<Color name="([^"]+)" value=")([^"]+)(")')
_ALIAS_RE = re.compile(r'(<ColorAlias name="([^"]+)" alias=")([^"]+)(")')


def _relative_luminance(rrggbbaa):
    channels = []
    for i in (0, 2, 4):
        c = int(rrggbbaa[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    """WCAG contrast ratio between two RRGGBBAA colours (alpha ignored)."""
    la, lb = _relative_luminance(a.lower()), _relative_luminance(b.lower())
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def generate(source=SOURCE, target=TARGET):
    text = Path(source).read_text(encoding="utf-8")

    def swap_color(m):
        return m.group(1) + COLORS.get(m.group(2), m.group(3)) + m.group(4)

    def swap_alias(m):
        return m.group(1) + ALIASES.get(m.group(2), m.group(3)) + m.group(4)

    text = _COLOR_RE.sub(swap_color, text)
    text = _ALIAS_RE.sub(swap_alias, text)

    # existing aliases retargeted to the new colours
    def swap_extra_alias(m):
        return m.group(1) + EXTRA_ALIASES.get(m.group(2), m.group(3)) + m.group(4)

    text = _ALIAS_RE.sub(swap_extra_alias, text)

    # new colours and new aliases appended once (idempotent on our own output)
    existing_colors = {m[1] for m in _COLOR_RE.findall(text)}
    existing_aliases = {m[1] for m in _ALIAS_RE.findall(text)}
    color_lines = "".join(
        f'    <Color name="{n}" value="{v}"/>\n'
        for n, v in EXTRA_COLORS.items() if n not in existing_colors
    )
    alias_lines = "".join(
        f'    <ColorAlias name="{n}" alias="{t}"/>\n'
        for n, t in EXTRA_ALIASES.items() if n not in existing_aliases
    )
    text = text.replace("  </Colors>", color_lines + "  </Colors>", 1)
    text = text.replace("  </ColorAliases>", alias_lines + "  </ColorAliases>", 1)

    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    generate()
    print(TARGET.relative_to(ROOT))
