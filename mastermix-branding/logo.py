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
"""Geometry of the MasterMix logo, emitted as SVG.

Direction "Faders": a bold M whose two legs are mixer channel strips,
each carrying a fader cap at a different position, and whose central V is
a single mitred stroke. Apple green on black.
"""

SIZE = 512
GREEN = "#A4DE02"
GREEN_LIGHT = "#C6F04A"
GREEN_DARK = "#8FC400"
BLACK = "#0A0A0A"
CAP_LINE = "#E8FFB0"

# Legs: (x, y, width, height, corner radius)
LEGS = [(88, 96, 80, 320, 14), (344, 96, 80, 320, 14)]
# Central V as a stroked polyline (x, y points) and its stroke width
V_POINTS = [(128, 120), (256, 300), (384, 120)]
V_WIDTH = 80
# Fader caps: (x, y, width, height, corner radius); the thin line sits inside
CAPS = [(74, 292, 108, 30, 7), (330, 212, 108, 30, 7)]
CAP_LINE_HEIGHT = 4
CAP_LINE_OFFSET = 13

VARIANTS = ("icon", "mono", "black")


def _rect(x, y, w, h, rx, fill):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>'


def build_svg(variant="icon"):
    """Return the SVG document for one variant.

    icon  : black rounded square + green gradient M (app icon)
    mono  : green gradient M on transparent background (splash)
    black : flat black M with white caps on transparent background (print)
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}, expected one of {VARIANTS}")

    background = ""
    if variant == "icon":
        background = f'<rect width="{SIZE}" height="{SIZE}" rx="112" fill="{BLACK}"/>'

    if variant == "black":
        gradient = ""
        fill = BLACK
        cap_fill, line_fill = "#FFFFFF", BLACK
    else:
        gradient = (
            '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{GREEN_LIGHT}"/>'
            f'<stop offset="1" stop-color="{GREEN_DARK}"/>'
            "</linearGradient>"
        )
        fill = "url(#g)"
        cap_fill, line_fill = BLACK, CAP_LINE

    points = " ".join(f"{x},{y}" for x, y in V_POINTS)
    v = (f'<polyline points="{points}" fill="none" stroke="{fill}" '
         f'stroke-width="{V_WIDTH}" stroke-linejoin="miter" stroke-miterlimit="4"/>')
    legs = "".join(_rect(*leg, fill) for leg in LEGS)
    caps = "".join(
        _rect(x, y, w, h, rx, cap_fill)
        + _rect(x, y + CAP_LINE_OFFSET, w, CAP_LINE_HEIGHT, 0, line_fill)
        for x, y, w, h, rx in CAPS
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" '
        f'viewBox="0 0 {SIZE} {SIZE}">\n'
        f"<defs>{gradient}</defs>\n"
        f"{background}{v}{legs}{caps}\n"
        "</svg>\n"
    )
