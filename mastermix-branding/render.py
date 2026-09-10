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
"""Rasterise the MasterMix logo into every asset Ardour's build expects.

Usage:  python mastermix-branding/render.py
Writes: gtk2_ardour/resources/MasterMix-*.png, gtk2_ardour/icons/MasterMix.ico,
        mastermix-branding/logo*.svg
"""
import io
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

# cairosvg needs libcairo-2.dll; on Windows we borrow it from MSYS2.
MSYS_BIN = Path(r"C:\msys64\mingw64\bin")
if os.name == "nt" and MSYS_BIN.is_dir():
    os.add_dll_directory(str(MSYS_BIN))
    os.environ["PATH"] = str(MSYS_BIN) + os.pathsep + os.environ.get("PATH", "")

import cairosvg  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import logo  # noqa: E402

NAME = "MasterMix"
ICON_SIZES = (16, 22, 32, 48, 256, 512)
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (256, 256)]
SPLASH_SIZE = (400, 348)
SMALL_SPLASH_SIZE = (100, 87)

DEFAULT_RES = ROOT / "gtk2_ardour" / "resources"
DEFAULT_ICONS = ROOT / "gtk2_ardour" / "icons"
DEFAULT_SVG = HERE


def svg_to_image(svg_text, size):
    png = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"),
                           output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _font(size):
    for candidate in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _centred_text(draw, text, font, y, width, fill):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (right - left)) // 2 - left, y), text, font=font, fill=fill)


def make_splash():
    width, height = SPLASH_SIZE
    img = Image.new("RGBA", SPLASH_SIZE, logo.BLACK)
    logo_px = 190
    mark = svg_to_image(logo.build_svg("mono"), logo_px)
    img.alpha_composite(mark, ((width - logo_px) // 2, 28))
    draw = ImageDraw.Draw(img)
    _centred_text(draw, "MASTERMIX", _font(44), 244, width, logo.GREEN)
    return img


def render_all(res_dir, icons_dir, svg_dir):
    res_dir, icons_dir, svg_dir = Path(res_dir), Path(icons_dir), Path(svg_dir)
    for d in (res_dir, icons_dir, svg_dir):
        d.mkdir(parents=True, exist_ok=True)
    written = []

    for variant in logo.VARIANTS:
        name = "logo.svg" if variant == "icon" else f"logo-{variant}.svg"
        path = svg_dir / name
        path.write_text(logo.build_svg(variant), encoding="utf-8")
        written.append(path)

    icon_svg = logo.build_svg("icon")
    for size in ICON_SIZES:
        path = res_dir / f"{NAME}-icon_{size}px.png"
        svg_to_image(icon_svg, size).save(path)
        written.append(path)

    ico = icons_dir / f"{NAME}.ico"
    svg_to_image(icon_svg, 256).save(ico, format="ICO", sizes=ICO_SIZES)
    written.append(ico)

    splash = make_splash()
    splash_path = res_dir / f"{NAME}-splash.png"
    splash.save(splash_path)
    written.append(splash_path)

    small_path = res_dir / f"{NAME}-small-splash.png"
    splash.resize(SMALL_SPLASH_SIZE, Image.LANCZOS).save(small_path)
    written.append(small_path)
    return written


def main():
    for path in render_all(DEFAULT_RES, DEFAULT_ICONS, DEFAULT_SVG):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
