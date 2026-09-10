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


def test_every_variant_is_valid_svg():
    for variant in ("icon", "mono", "black"):
        root = ET.fromstring(logo.build_svg(variant))
        assert root.tag.endswith("svg")
        assert root.get("viewBox") == f"0 0 {logo.SIZE} {logo.SIZE}"


def test_unknown_variant_rejected():
    with pytest.raises(ValueError):
        logo.build_svg("purple")


def test_icon_has_black_square_and_mono_does_not():
    assert "<rect" in logo.build_svg("icon")
    assert "<rect" not in logo.build_svg("mono")
    assert "<rect" not in logo.build_svg("black")


def test_black_variant_uses_flat_black_fill():
    svg = logo.build_svg("black")
    assert 'fill="#0A0A0A"' in svg
    assert "linearGradient" not in svg


def test_spikes_are_symmetric_and_deepest_under_the_legs():
    d = logo.spike_depths()
    assert len(d) == logo.SPIKE_COUNT
    assert d == d[::-1]
    assert d.index(max(d)) < len(d) // 4          # deepest under the left leg
    assert d[len(d) // 2] < 0.1 * max(d)         # almost nothing under the counter
    assert min(d) >= 0


def test_m_outline_is_mirror_symmetric_with_open_counter():
    pts = logo.M_POINTS
    assert len(pts) == 12
    mirrored = {(logo.SIZE - x, y) for x, y in pts}
    assert set(pts) == mirrored                          # symmetric about the centre
    xs, ys = zip(*pts)
    assert ys.count(min(ys)) == 4                        # four top corners
    assert ys.count(max(ys)) == 4                        # four base corners
    assert (256, 320) in pts and (256, 230) in pts       # V lower and upper vertex
    assert 320 == logo.BODY_BOTTOM                       # counter ends where spikes start


def test_wave_path_is_closed_and_uses_cubics():
    path = logo.wave_path()
    assert path.startswith("M 0 0")
    assert path.rstrip().endswith("Z")
    assert path.count(" C ") == 2 * logo.SPIKE_COUNT
