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
import pytest

render = pytest.importorskip("render")   # skipped when cairo DLLs are missing
from PIL import Image  # noqa: E402


def test_render_all_writes_every_asset_with_exact_sizes(tmp_path):
    res = tmp_path / "resources"
    icons = tmp_path / "icons"
    svgs = tmp_path / "svg"
    written = render.render_all(res, icons, svgs)

    expected_png = {
        "MasterMix-icon_16px.png": (16, 16),
        "MasterMix-icon_22px.png": (22, 22),
        "MasterMix-icon_32px.png": (32, 32),
        "MasterMix-icon_48px.png": (48, 48),
        "MasterMix-icon_256px.png": (256, 256),
        "MasterMix-icon_512px.png": (512, 512),
        "MasterMix-splash.png": (400, 348),
        "MasterMix-small-splash.png": (100, 87),
    }
    for name, size in expected_png.items():
        path = res / name
        assert path in written
        assert Image.open(path).size == size

    ico = icons / "MasterMix.ico"
    assert ico in written
    with Image.open(ico) as im:
        assert im.format == "ICO"
        assert (256, 256) in im.info["sizes"]
        assert (16, 16) in im.info["sizes"]

    for name in ("logo.svg", "logo-mono.svg", "logo-black.svg"):
        assert (svgs / name) in written


def test_icon_centre_is_green_and_corner_is_black(tmp_path):
    render.render_all(tmp_path / "r", tmp_path / "i", tmp_path / "s")
    im = Image.open(tmp_path / "r" / "MasterMix-icon_256px.png").convert("RGBA")
    r, g, b, a = im.getpixel((60, 120))          # inside the left leg of the M
    assert g > 150 and g > r and g > b and a == 255
    r, g, b, a = im.getpixel((2, 2))             # rounded corner is transparent
    assert a == 0
    r, g, b, a = im.getpixel((30, 30))           # black square
    assert (r, g, b) == (10, 10, 10) and a == 255


def test_splash_is_black_with_green_title(tmp_path):
    render.render_all(tmp_path / "r", tmp_path / "i", tmp_path / "s")
    im = Image.open(tmp_path / "r" / "MasterMix-splash.png").convert("RGB")
    assert im.getpixel((5, 5)) == (10, 10, 10)
    greens = sum(
        1 for x in range(0, 400, 4) for y in range(240, 300, 4)
        if (lambda p: p[1] > 150 and p[1] > p[0] and p[1] > p[2])(im.getpixel((x, y)))
    )
    assert greens > 40, "title text should be rendered in apple green"
