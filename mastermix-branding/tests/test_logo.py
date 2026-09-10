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

import pytest

import logo

NS = "{http://www.w3.org/2000/svg}"


def test_every_variant_is_valid_svg():
    for variant in ("icon", "mono", "black"):
        root = ET.fromstring(logo.build_svg(variant))
        assert root.tag.endswith("svg")
        assert root.get("viewBox") == f"0 0 {logo.SIZE} {logo.SIZE}"


def test_unknown_variant_rejected():
    with pytest.raises(ValueError):
        logo.build_svg("purple")


def test_icon_has_black_square_and_mono_does_not():
    icon = ET.fromstring(logo.build_svg("icon"))
    mono = ET.fromstring(logo.build_svg("mono"))
    full = [r for r in icon.iter(NS + "rect") if r.get("width") == str(logo.SIZE)]
    assert len(full) == 1 and full[0].get("fill") == logo.BLACK
    assert not [r for r in mono.iter(NS + "rect") if r.get("width") == str(logo.SIZE)]


def test_black_variant_uses_flat_black_fill():
    svg = logo.build_svg("black")
    assert "linearGradient" not in svg
    assert 'stroke="#0A0A0A"' in svg


def test_legs_are_mirror_symmetric():
    (x1, y1, w1, h1, r1), (x2, y2, w2, h2, r2) = logo.LEGS
    assert (y1, w1, h1, r1) == (y2, w2, h2, r2)
    assert x1 + x2 + w1 == logo.SIZE                 # symmetric about the centre


def test_v_is_centred_and_touches_both_legs():
    (ax, ay), (mx, my), (bx, by) = logo.V_POINTS
    assert mx == logo.SIZE // 2 and ay == by
    assert my > ay                                   # vertex below the arms
    assert ax + bx == logo.SIZE
    left_leg, right_leg = logo.LEGS
    assert ax <= left_leg[0] + left_leg[2]           # arm starts inside the left leg
    assert bx >= right_leg[0]                        # and ends inside the right leg


def test_two_fader_caps_at_different_heights_over_each_leg():
    assert len(logo.CAPS) == 2
    (cx1, cy1, cw1, _, _), (cx2, cy2, cw2, _, _) = logo.CAPS
    assert cy1 != cy2
    left_leg, right_leg = logo.LEGS
    assert cx1 < left_leg[0] and cx1 + cw1 > left_leg[0] + left_leg[2]   # cap overhangs the leg
    assert cx2 < right_leg[0] and cx2 + cw2 > right_leg[0] + right_leg[2]
    icon = ET.fromstring(logo.build_svg("icon"))
    caps = [r for r in icon.iter(NS + "rect") if r.get("fill") == logo.BLACK and r.get("rx") == "7"]
    assert len(caps) == 2
