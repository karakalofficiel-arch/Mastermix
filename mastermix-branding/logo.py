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

The logo mirrors Ardour's: a solid glyph whose lower edge is eaten by an
audio-waveform envelope (a row of rounded spikes pointing down, deepest in
the middle).  Ardour uses a triangle for the "A"; MasterMix uses a solid
two-peak silhouette for the "M".
"""
import math

SIZE = 512
GREEN = "#A4DE02"
GREEN_LIGHT = "#C6F04A"
GREEN_DARK = "#7FAE00"
BLACK = "#0A0A0A"

# Solid "M" silhouette, left to right: base-left, peak-left, valley, peak-right, base-right.
M_POINTS = [(40, 440), (150, 72), (256, 236), (362, 72), (472, 440)]

BODY_BOTTOM = 300        # y where the solid body ends; spikes hang below it
SPIKE_COUNT = 13
SPIKE_MAX_DEPTH = 140    # deepest spike, in px below BODY_BOTTOM
SPIKE_X0 = 40            # spikes span the width of the M base
SPIKE_X1 = 472

VARIANTS = ("icon", "mono", "black")


def spike_depths(count=SPIKE_COUNT, max_depth=SPIKE_MAX_DEPTH):
    """Depth of each spike, bell-shaped and alternating long/short like a waveform."""
    centre = (count - 1) / 2
    sigma = count / 3.2
    depths = []
    for i in range(count):
        bell = math.exp(-((i - centre) / sigma) ** 2)
        wobble = 0.85 if i % 2 else 1.0
        depths.append(round(max_depth * bell * wobble, 1))
    return depths


def wave_path(body_bottom=BODY_BOTTOM, x0=SPIKE_X0, x1=SPIKE_X1):
    """Closed path of the region to KEEP: everything above the waveform edge.

    Walks the bottom edge right-to-left; each spike is two cubic Béziers
    (trough -> rounded tip -> trough)."""
    depths = spike_depths()
    n = len(depths)
    span = (x1 - x0) / n
    parts = [f"M 0 0 L {SIZE} 0 L {SIZE} {body_bottom} L {x1} {body_bottom}"]
    for i in reversed(range(n)):
        left = x0 + span * i
        right = left + span
        cx = (left + right) / 2
        tip = body_bottom + depths[i]
        shoulder = body_bottom + depths[i] * 0.55
        parts.append(
            f"C {right:.1f} {shoulder:.1f} {cx + span * 0.18:.1f} {tip:.1f} {cx:.1f} {tip:.1f}"
        )
        parts.append(
            f"C {cx - span * 0.18:.1f} {tip:.1f} {left:.1f} {shoulder:.1f} {left:.1f} {body_bottom}"
        )
    parts.append(f"L 0 {body_bottom} Z")
    return " ".join(parts)


def build_svg(variant="icon"):
    """Return the SVG document for one variant.

    icon  : black rounded square + green gradient M (app icon)
    mono  : green gradient M on transparent background (splash)
    black : flat black M on transparent background (print)
    """
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}, expected one of {VARIANTS}")

    points = " ".join(f"{x},{y}" for x, y in M_POINTS)
    background = ""
    if variant == "icon":
        background = f'<rect width="{SIZE}" height="{SIZE}" rx="92" fill="{BLACK}"/>'

    if variant == "black":
        gradient = ""
        fill = BLACK
    else:
        gradient = (
            '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{GREEN_LIGHT}"/>'
            f'<stop offset="1" stop-color="{GREEN_DARK}"/>'
            "</linearGradient>"
        )
        fill = "url(#g)"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" '
        f'viewBox="0 0 {SIZE} {SIZE}">\n'
        f'<defs>{gradient}<clipPath id="wave"><path d="{wave_path()}"/></clipPath></defs>\n'
        f'{background}<polygon points="{points}" fill="{fill}" clip-path="url(#wave)"/>\n'
        "</svg>\n"
    )
