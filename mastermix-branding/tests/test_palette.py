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
import xml.etree.ElementTree as ET
from pathlib import Path

import palette

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "gtk2_ardour" / "themes" / "dark-ardour.colors"


def _colors(xml_text):
    root = ET.fromstring(xml_text)
    return {c.get("name"): c.get("value") for c in root.find("Colors")}


def _aliases(xml_text):
    root = ET.fromstring(xml_text)
    return {a.get("name"): a.get("alias") for a in root.find("ColorAliases")}


def test_every_override_targets_an_existing_upstream_name():
    src = SOURCE.read_text(encoding="utf-8")
    missing = set(palette.COLORS) - set(_colors(src))
    assert not missing, f"unknown colour names: {missing}"
    missing = set(palette.ALIASES) - set(_aliases(src))
    assert not missing, f"unknown alias names: {missing}"
    for target in palette.ALIASES.values():
        assert target in _colors(src), target


def test_generate_applies_overrides_and_keeps_everything_else(tmp_path):
    out = tmp_path / "dark-mastermix.colors"
    xml_text = palette.generate(SOURCE, out)
    assert out.read_text(encoding="utf-8") == xml_text

    src_colors = _colors(SOURCE.read_text(encoding="utf-8"))
    new_colors = _colors(xml_text)
    assert set(new_colors) == set(src_colors) | set(palette.EXTRA_COLORS)
    for name, value in palette.COLORS.items():
        assert new_colors[name] == value
    untouched = [n for n in src_colors if n not in palette.COLORS]
    for name in untouched:
        assert new_colors[name] == src_colors[name]

    new_aliases = _aliases(xml_text)
    for name, target in palette.ALIASES.items():
        assert new_aliases[name] == target


def test_playhead_and_record_stay_red(tmp_path):
    xml_text = palette.generate(SOURCE, tmp_path / "t.colors")
    colors = _colors(xml_text)
    assert colors["theme:contrasting"].lower().endswith("f10000ff")
    assert colors["alert:red"] == "f10000ff"


def test_selection_text_is_readable_on_apple_green(tmp_path):
    xml_text = palette.generate(SOURCE, tmp_path / "t.colors")
    colors, aliases = _colors(xml_text), _aliases(xml_text)
    bg = colors[aliases["gtk_bg_selected"]]
    fg = colors[aliases["gtk_fg_selected"]]
    assert palette.contrast_ratio(fg, bg) >= 7.0


def test_accent_on_background_meets_aaa():
    assert palette.contrast_ratio("a4de02ff", "0a0a0aff") >= 7.0
    assert palette.contrast_ratio("e8e8e8ff", "0a0a0aff") >= 7.0


def test_extra_colors_are_added_and_aliases_point_to_them(tmp_path):
    xml_text = palette.generate(SOURCE, tmp_path / "t.colors")
    colors, aliases = _colors(xml_text), _aliases(xml_text)
    for name, value in palette.EXTRA_COLORS.items():
        assert colors[name] == value
    for alias, target in palette.EXTRA_ALIASES.items():
        assert aliases[alias] == target
        assert target in colors


def test_extra_colors_are_new_names_and_alias_targets_exist():
    src = SOURCE.read_text(encoding="utf-8")
    assert not set(palette.EXTRA_COLORS) & set(_colors(src))
    for target in palette.EXTRA_ALIASES.values():
        assert target in palette.EXTRA_COLORS or target in _colors(src)


def test_track_header_colors_by_type(tmp_path):
    xml_text = palette.generate(SOURCE, tmp_path / "t.colors")
    colors, aliases = _colors(xml_text), _aliases(xml_text)
    assert colors[aliases["gtk_audio_track"]] == "1c2733ff"
    assert colors[aliases["gtk_midi_track"]] == "332a1cff"
    assert colors[aliases["gtk_audio_bus"]] == "1f2e14ff"
    assert colors[aliases["gtk_master_bus"]] == "33141cff"
    for alias in ("gtk_audio_track", "gtk_midi_track", "gtk_audio_bus", "gtk_master_bus"):
        assert palette.contrast_ratio("e8e8e8ff", colors[aliases[alias]]) >= 7.0


def test_generate_is_idempotent_on_its_own_output(tmp_path):
    first = tmp_path / "first.colors"
    palette.generate(SOURCE, first)
    second = palette.generate(first, tmp_path / "second.colors")
    assert second == first.read_text(encoding="utf-8")
