# MasterMix Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a Windows x64 build of Ardour 9.8 rebranded as MasterMix, with an apple-green/black theme, an "M" logo derived from Ardour's, and an NSIS installer.

**Architecture:** The repo is an Ardour 9.8 checkout on branch `mastermix`. Branding uses Ardour's built-in `--program-name` mechanism (resources selected by filename), so almost no C++ changes. Logo, icons, splash and theme are *generated* by small Python scripts in `mastermix-branding/` so they can be regenerated after a rebase. Build and packaging scripts for MSYS2 live in `tools/mastermix/`.

**Tech Stack:** Ardour 9.8 (C++, waf), MSYS2 MINGW64 (gcc), Python 3.12 (system, `C:\...\Python312\python.exe`) with `cairosvg`, `Pillow`, `pytest`; NSIS via MSYS2.

**Spec:** `docs/superpowers/specs/2026-09-10-mastermix-phase1-design.md`

## Global Constraints

- Licence GPLv2+ inchangée; `COPYING` intact.
- Every new file starts with a header: `Copyright (C) 2026 Ahmed Hadjadj` + GPLv2+ notice (see Task 1 for the exact text).
- Git author: `Ahmed Hadjadj <karakalofficiel@gmail.com>` (already set in repo-local config). Commit messages end with the Claude attribution lines.
- Never rename XML node names `"Ardour"` in `rc_configuration.cc`, `session_configuration.cc`, `session_state.cc`, `ui_config.cc`, `utils.cc`, nor the Lua namespace `Ardour` in `luaproc.cc`.
- Program name is exactly `MasterMix` (capital M, capital M). Lowercase form `mastermix` is derived by Ardour.
- Accent colour `#A4DE02`; dark accent `#7FAE00`; light accent `#C6F04A`; main background `#0A0A0A`.
- Splash sizes: `MasterMix-splash.png` 400×348, `MasterMix-small-splash.png` 100×87. Icon sizes: 16, 22, 32, 48, 256, 512.
- MSYS2 is installed at `C:\msys64`. Invoke it from Git Bash as:
  `MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc '<command>'`
  (run from the repo root so `CHERE_INVOKING` keeps the cwd).
- System Python is used for the branding scripts: `python` on PATH = Python 3.12. Tests run with `python -m pytest`.
- Playhead and record colours stay red.

---

### Task 1: Branding scaffold, README, logo geometry (`logo.py`)

**Files:**
- Create: `README.md`
- Create: `mastermix-branding/__init__.py` (empty)
- Create: `mastermix-branding/logo.py`
- Create: `mastermix-branding/requirements.txt`
- Test: `mastermix-branding/tests/test_logo.py`
- Create: `mastermix-branding/tests/conftest.py`

**Interfaces:**
- Produces: `logo.build_svg(variant: str) -> str` where `variant in ("icon", "mono", "black")`; constants `SIZE = 512`, `GREEN = "#A4DE02"`, `GREEN_LIGHT = "#C6F04A"`, `GREEN_DARK = "#7FAE00"`, `BLACK = "#0A0A0A"`, `M_POINTS`, `spike_depths() -> list[float]`, `wave_path() -> str`.

Header to put at the top of every new Python file (Task 1, 2, 3):

```python
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
```

- [ ] **Step 1: Install Python deps and write `requirements.txt`**

`mastermix-branding/requirements.txt`:
```
cairosvg>=2.7
Pillow>=10
pytest>=8
```
Run: `python -m pip install -r mastermix-branding/requirements.txt`
Expected: exit 0.

- [ ] **Step 2: Write `conftest.py` so tests import `logo` without packaging**

`mastermix-branding/tests/conftest.py`:
```python
# (GPL header as above)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```
Create empty `mastermix-branding/__init__.py`.

- [ ] **Step 3: Write the failing tests**

`mastermix-branding/tests/test_logo.py`:
```python
# (GPL header as above)
import xml.etree.ElementTree as ET

import logo


def test_every_variant_is_valid_svg():
    for variant in ("icon", "mono", "black"):
        root = ET.fromstring(logo.build_svg(variant))
        assert root.tag.endswith("svg")
        assert root.get("viewBox") == f"0 0 {logo.SIZE} {logo.SIZE}"


def test_unknown_variant_rejected():
    import pytest
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


def test_spikes_are_symmetric_and_tallest_in_middle():
    d = logo.spike_depths()
    assert len(d) == logo.SPIKE_COUNT
    assert d == d[::-1]
    assert max(d) == d[len(d) // 2]
    assert min(d) > 0


def test_m_silhouette_has_two_peaks_and_central_valley():
    xs, ys = zip(*logo.M_POINTS)
    assert len(logo.M_POINTS) == 5
    assert ys[1] == ys[3] == min(ys)          # two peaks at the top
    assert ys[1] < ys[2] < ys[0]              # valley between peaks, above the base
    assert ys[0] == ys[4] == max(ys)          # flat base
    assert xs == tuple(sorted(xs))            # left to right
    assert xs[0] + xs[4] == logo.SIZE         # horizontally centred


def test_wave_path_is_closed_and_uses_cubics():
    path = logo.wave_path()
    assert path.startswith("M 0 0")
    assert path.rstrip().endswith("Z")
    assert path.count(" C ") == 2 * logo.SPIKE_COUNT
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest mastermix-branding/tests/test_logo.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'logo'`.

- [ ] **Step 5: Write `logo.py`**

`mastermix-branding/logo.py`:
```python
# (GPL header as above)
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest mastermix-branding/tests/test_logo.py -q`
Expected: `8 passed`.

- [ ] **Step 7: Write `README.md`**

`README.md`:
```markdown
# MasterMix

MasterMix est une station audionumérique (DAW) pour Windows, dérivée
d'[Ardour](https://ardour.org/) 9.8. Elle conserve l'intégralité des
fonctions d'Ardour avec une identité visuelle vert pomme et noir.

Auteur : Ahmed Hadjadj — 2026.
Licence : GNU GPL version 2 ou ultérieure (voir `COPYING`).
Ardour est © 1999-2026 Paul Davis et contributeurs. « Ardour » est une
marque de Paul Davis ; MasterMix n'est pas affilié au projet Ardour.

## Construire sous Windows (MSYS2 MINGW64)

1. Installer MSYS2 (https://www.msys2.org/) dans `C:\msys64`.
2. Depuis un shell MINGW64, à la racine du dépôt :
   ```
   tools/mastermix/setup-msys2.sh   # installe les dépendances
   tools/mastermix/build.sh          # configure + compile
   tools/mastermix/package-msys2.sh  # produit l'installeur NSIS
   ```
3. Le binaire est dans `build/gtk2_ardour/`, l'installeur dans `dist/`.

## Identité visuelle

Logo, icônes, splash et thème sont générés par les scripts de
`mastermix-branding/` (`python mastermix-branding/render.py`,
`python mastermix-branding/palette.py`).

## Dépôt

Branche `mastermix`, basée sur le tag Ardour `9.8`. Remote `upstream`
= https://github.com/Ardour/ardour.git. Les modifications MasterMix sont
des commits par-dessus le tag, pour rebaser sur les versions futures.
```

- [ ] **Step 8: Commit**

```bash
git add README.md mastermix-branding/
git commit -m "feat(branding): MasterMix README and logo geometry module

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```

---

### Task 2: Rasterise logo, icons, `.ico` and splash (`render.py`)

**Files:**
- Create: `mastermix-branding/render.py`
- Create (generated, committed): `mastermix-branding/logo.svg`, `logo-mono.svg`, `logo-black.svg`
- Create (generated, committed): `gtk2_ardour/resources/MasterMix-icon_{16,22,32,48,256,512}px.png`, `gtk2_ardour/resources/MasterMix-splash.png`, `gtk2_ardour/resources/MasterMix-small-splash.png`, `gtk2_ardour/icons/MasterMix.ico`
- Test: `mastermix-branding/tests/test_render.py`

**Interfaces:**
- Consumes: `logo.build_svg`, `logo.GREEN`, `logo.BLACK`.
- Produces: `render.render_all(res_dir: Path, icons_dir: Path, svg_dir: Path) -> list[Path]` returning every file written; `render.main()` writes into the real repo paths.

Prerequisite: `C:\msys64\mingw64\bin\libcairo-2.dll` must exist. Install it (idempotent):
```
MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc 'pacman -S --needed --noconfirm mingw-w64-x86_64-cairo'
```

- [ ] **Step 1: Write the failing test**

`mastermix-branding/tests/test_render.py`:
```python
# (GPL header as above)
import pytest

render = pytest.importorskip("render")   # skipped when cairo DLLs are missing
from PIL import Image


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
    r, g, b, a = im.getpixel((100, 200))         # inside the left leg of the M
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
        1 for x in range(0, 400, 4) for y in range(225, 285, 4)
        if (lambda p: p[1] > 150 and p[1] > p[0] and p[1] > p[2])(im.getpixel((x, y)))
    )
    assert greens > 40, "title text should be rendered in apple green"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest mastermix-branding/tests/test_render.py -q`
Expected: `3 skipped` (module `render` missing). That counts as "failing" for this task: the module must exist and the tests must actually run.

- [ ] **Step 3: Write `render.py`**

`mastermix-branding/render.py`:
```python
# (GPL header as above)
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
SUBTITLE = "basé sur Ardour 9.8"
GREY = "#8A8A8A"

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
    _centred_text(draw, "MASTERMIX", _font(44), 228, width, logo.GREEN)
    _centred_text(draw, SUBTITLE, _font(15), 296, width, GREY)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest mastermix-branding/tests -q`
Expected: `11 passed`. If `test_render.py` is *skipped*, cairo is missing: run the pacman command in the prerequisite and retry. If `test_icon_centre_is_green...` fails on the pixel at (100, 200), open the PNG and adjust the sample point to a pixel inside the left leg; do not loosen the colour assertion.

- [ ] **Step 5: Generate the real assets and inspect them**

Run: `python mastermix-branding/render.py`
Expected: prints 12 paths. Then view `gtk2_ardour/resources/MasterMix-icon_256px.png` and `MasterMix-splash.png` (Read tool). Acceptance: the shape reads as an M with a waveform bottom edge like Ardour's triangle; text is centred and not clipped. If the M looks like two mountains, lower the valley (`M_POINTS[2]` y from 236 to ~300) and re-run Task 1 tests + this step.

- [ ] **Step 6: Commit**

```bash
git add mastermix-branding/ gtk2_ardour/resources/MasterMix-* gtk2_ardour/icons/MasterMix.ico
git commit -m "feat(branding): render MasterMix logo, icons, ico and splash

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```

---

### Task 3: Apple-green/black theme generator (`palette.py`)

**Files:**
- Create: `mastermix-branding/palette.py`
- Create (generated, committed): `gtk2_ardour/themes/dark-mastermix.colors`
- Test: `mastermix-branding/tests/test_palette.py`

**Interfaces:**
- Consumes: `gtk2_ardour/themes/dark-ardour.colors` (upstream; XML with `<Color name value>` inside `<Colors>` and `<ColorAlias name alias>` inside `<ColorAliases>`).
- Produces: `palette.generate(source: Path, target: Path) -> str` (returns the XML written); dicts `palette.COLORS` and `palette.ALIASES`.

Background: the Ardour theme file has ~57 base colours and ~429 aliases that point at them. Recolouring the base colours retints the whole UI. Names must match upstream exactly (spaces included, e.g. `theme:contrasting clock`).

- [ ] **Step 1: Write the failing tests**

`mastermix-branding/tests/test_palette.py`:
```python
# (GPL header as above)
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
    assert set(new_colors) == set(src_colors)
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest mastermix-branding/tests/test_palette.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'palette'`.

- [ ] **Step 3: Write `palette.py`**

`mastermix-branding/palette.py`:
```python
# (GPL header as above)
"""Generate gtk2_ardour/themes/dark-mastermix.colors from Ardour's dark theme.

Usage:  python mastermix-branding/palette.py
Only the base colours listed in COLORS and the aliases in ALIASES change;
every other entry is copied verbatim so the file stays rebase-friendly.
"""
import re
import sys
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
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    Path(target).write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    generate()
    print(TARGET.relative_to(ROOT))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest mastermix-branding/tests/test_palette.py -q`
Expected: `5 passed`. If `test_every_override_targets_an_existing_upstream_name` fails, fix the *key spelling* in `COLORS`/`ALIASES` to match upstream; never delete the override.

- [ ] **Step 5: Generate the theme file**

Run: `python mastermix-branding/palette.py`
Expected: `gtk2_ardour/themes/dark-mastermix.colors` written; `git diff --no-index gtk2_ardour/themes/dark-ardour.colors gtk2_ardour/themes/dark-mastermix.colors | grep -c '^[-+]<' ` is roughly 60 (about 25 colours + 5 aliases, two lines each). Not more than 80.

- [ ] **Step 6: Commit**

```bash
git add mastermix-branding/palette.py mastermix-branding/tests/test_palette.py gtk2_ardour/themes/dark-mastermix.colors
git commit -m "feat(theme): apple-green on black dark-mastermix theme, generated from dark-ardour

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```

---

### Task 4: About dialog credits

**Files:**
- Modify: `gtk2_ardour/about.cc:131` (authors array head) and `gtk2_ardour/about.cc:647-652` (copyright / website block)

**Interfaces:** none (UI text only).

- [ ] **Step 1: Add the author**

In `gtk2_ardour/about.cc`, the array starts at line 131:
```cpp
static const char* authors[] = {
	N_("Fons Adriaensen"),
```
Change to:
```cpp
static const char* authors[] = {
	N_("Ahmed Hadjadj (MasterMix)"),
	N_("Fons Adriaensen"),
```

- [ ] **Step 2: Rewrite the copyright / comments block**

Replace, near line 647:
```cpp
	set_translator_credits (t);
	set_copyright (_("Copyright (C) 1999-2026 Paul Davis\n"));
	set_license (gpl);
	set_name (X_("Ardour"));
	set_website (X_("https://ardour.org/"));
	set_website_label (_("http://ardour.org/"));
```
with:
```cpp
	set_translator_credits (t);
	set_copyright (_("MasterMix Copyright (C) 2026 Ahmed Hadjadj\n"
	                 "Based on Ardour, Copyright (C) 1999-2026 Paul Davis\n"));
	set_comments (_("MasterMix is a derivative of the Ardour digital audio workstation.\n"
	                "Ardour is a trademark of Paul Davis; MasterMix is not affiliated with the Ardour project."));
	set_license (gpl);
	set_name (X_("Ardour"));
	set_website (X_("https://ardour.org/"));
	set_website_label (_("Ardour manual and website"));
```
`set_name` stays: it is the GTK widget name used by the style engine, not a display string.

- [ ] **Step 3: Verify it still parses (no build yet)**

Run: `grep -n "Ahmed Hadjadj" gtk2_ardour/about.cc`
Expected: two hits (authors array, copyright). Compilation is verified in Task 6.

- [ ] **Step 4: Commit**

```bash
git add gtk2_ardour/about.cc
git commit -m "feat(about): MasterMix credits and Ardour attribution in About dialog

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```

---

### Task 5: MSYS2 dependency setup script

**Files:**
- Create: `tools/mastermix/setup-msys2.sh`
- Create: `tools/mastermix/README.md`

**Interfaces:**
- Produces: a MINGW64 environment where `pkg-config --exists` succeeds for every module listed in Step 3.

Shell-script header (use in every `tools/mastermix/*.sh`):
```bash
#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
```

- [ ] **Step 1: Write the script**

`tools/mastermix/setup-msys2.sh`:
```bash
#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Install every package MasterMix needs to build under MSYS2 MINGW64.
# Run from a MINGW64 shell (or via
#   MSYSTEM=MINGW64 /c/msys64/usr/bin/bash.exe -lc tools/mastermix/setup-msys2.sh).
set -euo pipefail

if [ "${MSYSTEM:-}" != "MINGW64" ]; then
	echo "error: run this from an MSYS2 MINGW64 shell (MSYSTEM=$MSYSTEM)" >&2
	exit 1
fi

P=mingw-w64-x86_64

MSYS_PKGS=(base-devel git)

MINGW_PKGS=(
	$P-toolchain $P-pkgconf $P-python $P-ntldd $P-nsis
	$P-boost $P-glib2 $P-glibmm $P-libsigc++ $P-libxml2
	$P-cairo $P-cairomm $P-pango $P-pangomm $P-fontconfig $P-libpng $P-gdk-pixbuf2
	$P-libsndfile $P-flac $P-libogg $P-libsamplerate $P-soundtouch $P-rubberband $P-aubio $P-fftw
	$P-curl $P-libarchive $P-liblo $P-taglib $P-libusb $P-libwebsockets
	$P-lv2 $P-lilv $P-serd $P-sord $P-sratom $P-suil
	$P-vamp-plugin-sdk $P-cppunit $P-portaudio $P-jack2 $P-readline
)

pacman -Sy --noconfirm
pacman -S --needed --noconfirm "${MSYS_PKGS[@]}"
pacman -S --needed --noconfirm "${MINGW_PKGS[@]}"

echo "--- pkg-config check"
MODULES="glib-2.0 gthread-2.0 glibmm-2.4 giomm-2.4 sigc++-2.0 cairomm-1.0 pangomm-1.4 pangocairo
sndfile samplerate rubberband aubio fftw3f libcurl libarchive liblo taglib libusb-1.0
lv2 lilv-0 serd-0 sord-0 sratom-0 vamp-sdk vamp-hostsdk cppunit portaudio-2.0 jack libwebsockets libxml-2.0"
missing=0
for m in $MODULES; do
	if pkg-config --exists "$m"; then
		printf '  ok   %s %s\n' "$m" "$(pkg-config --modversion "$m")"
	else
		printf '  MISS %s\n' "$m"; missing=1
	fi
done
exit $missing
```

`tools/mastermix/README.md`:
```markdown
# MasterMix build scripts (MSYS2 MINGW64)

- `setup-msys2.sh`   installe les dépendances pacman et vérifie pkg-config.
- `build.sh`         `waf configure` + `waf build` avec `--program-name=MasterMix`.
- `package-msys2.sh` assemble `dist/MasterMix/` et produit l'installeur NSIS.
- `patches/`         patches de build MinGW appliqués en commits séparés (vide si aucun).

Tous les scripts s'exécutent depuis la racine du dépôt.
```

- [ ] **Step 2: Run it**

Run (from repo root, Git Bash):
```
chmod +x tools/mastermix/*.sh
MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc 'tools/mastermix/setup-msys2.sh' 2>&1 | tail -40
```
Expected: every module line prints `ok`, exit 0. Download is ~1.5 GB; allow 10-20 min. If a package name is not found, look it up with `pacman -Ss <name>` and fix the list (do not drop the dependency). If `glibmm-2.4` is missing but `glibmm-2.68` is present, the package `mingw-w64-x86_64-glibmm` is the 2.4 one; install it explicitly.

- [ ] **Step 3: Commit**

```bash
git add tools/mastermix/setup-msys2.sh tools/mastermix/README.md
git commit -m "build(msys2): dependency install script for MINGW64

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```

---

### Task 6: Configure and build with waf

**Files:**
- Create: `tools/mastermix/build.sh`
- Create: `tools/mastermix/patches/.gitkeep`
- Possibly modify: upstream sources, one commit per MinGW fix.

**Interfaces:**
- Produces: `build/gtk2_ardour/mastermix-9.8.0.exe` (name may be `mastermix-9.8.exe`; check `ls build/gtk2_ardour/*.exe`), `build/libs/**/*.dll`, `build/gtk2_ardour/windows_icon.rc` referencing `icons/MasterMix.ico`.

- [ ] **Step 1: Write `build.sh`**

`tools/mastermix/build.sh`:
```bash
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
	--program-name=MasterMix
	--dist-target=mingw
	--with-backends=portaudio,dummy,jack
	--optimize
	--no-lrdf
	--no-phone-home
	--prefix=/mingw64
)

case "${1:-build}" in
	clean)
		$PYTHON ./waf clean
		exit 0
		;;
	configure)
		$PYTHON ./waf configure "${CONFIGURE_FLAGS[@]}"
		;;
	build)
		if [ ! -f build/c4che/_cache.py ]; then
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
```

- [ ] **Step 2: Configure**

Run:
```
MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc 'tools/mastermix/build.sh configure' 2>&1 | tail -60
```
Expected: ends with `'configure' finished successfully`. Then check:
```
grep -n "MasterMix" build/c4che/_cache.py | head -3
cat gtk2_ardour/windows_icon.rc
```
Expected: `PROGRAM_NAME = 'MasterMix'` and `IDI_ICON1 ICON DISCARDABLE "icons/MasterMix.ico"`.

If configure fails on a missing dependency, add the package to `setup-msys2.sh` (Task 5) and re-run. If it fails on a compiler/flag check, read `build/config.log` for the failing snippet before changing anything.

- [ ] **Step 3: Build (long: 30-90 min)**

Run in the background with a 10-minute tool timeout, logging to a file:
```
MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc 'tools/mastermix/build.sh build > build-mastermix.log 2>&1; echo EXIT=$? >> build-mastermix.log'
```
Poll with `tail -5 build-mastermix.log` and `grep -n "error:" build-mastermix.log | head`.

For each compile error:
1. Read the failing source line and the error text.
2. Make the smallest fix that keeps upstream behaviour (usually a missing `#include <...>`, a `#ifdef PLATFORM_WINDOWS` guard, or a MinGW type mismatch).
3. Save the diff as `tools/mastermix/patches/NNNN-<short-name>.patch` (`git diff > ...`) AND commit the fix on its own:
   `git commit -am "fix(mingw): <what> (<file>)"` with the attribution trailer.
4. Re-run the build command.

Expected final state: `EXIT=0` in the log and `build/gtk2_ardour/mastermix-*.exe` present.

- [ ] **Step 4: Sanity check the binary's branding**

Run:
```
strings -el build/gtk2_ardour/mastermix-*.exe | grep -c MasterMix ; strings build/gtk2_ardour/mastermix-*.exe | grep -c "MasterMix"
```
Expected: at least one non-zero count (the `PROGRAM_NAME` literal is compiled in).

- [ ] **Step 5: Commit the build script (and `.gitkeep`)**

```bash
git add tools/mastermix/build.sh tools/mastermix/patches/.gitkeep
git commit -m "build(msys2): waf configure/build wrapper with MasterMix program name

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```
Add `build-mastermix.log` to `.git/info/exclude` (not to `.gitignore`, to keep the upstream file untouched).

---

### Task 7: Run from the build tree and verify branding + theme

**Files:**
- Create: `tools/mastermix/run-dev.sh`
- Screenshots go to the scratchpad, not the repo.

**Interfaces:**
- Consumes: Task 6 binary; Ardour's dev launcher `gtk2_ardour/ardev` (sets `ARDOUR_DATA_PATH`, `ARDOUR_CONFIG_PATH`, etc. so resources are found in-tree). Read `gtk2_ardour/ardev_common.sh.in` to see the variables.

- [ ] **Step 1: Write `run-dev.sh`**

`tools/mastermix/run-dev.sh`:
```bash
#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Launch the freshly built MasterMix from the build tree (MSYS2 MINGW64).
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="$PWD/build/libs/pbd:$PWD/build/libs/ardour:$PWD/build/libs/gtkmm2ext:$PWD/build/libs/widgets:$PWD/build/libs/canvas:$PWD/build/libs/waveview:$PWD/build/libs/temporal:$PWD/build/libs/evoral:$PWD/build/libs/midi++2:$PWD/build/libs/audiographer:$PWD/build/libs/tk/ytk:$PWD/build/libs/tk/ydk:$PWD/build/libs/tk/ytkmm:$PWD/build/libs/tk/ydkmm:$PWD/build/libs/tk/ztk:$PWD/build/libs/tk/ztkmm:$PWD/build/libs/tk/suil:$PWD/build/libs/lua:$PWD/build/libs/fluidsynth:$PWD/build/libs/zita-resampler:$PWD/build/libs/zita-convolver:$PWD/build/libs/qm-dsp:$PWD/build/libs/vamp-plugins:$PWD/build/libs/ptformat:$PWD/build/libs/aaf:$PWD/build/libs/ctrl-interface/control_protocol:$PWD/build/libs/ctrl-interface/midi_surface:$PWD/build/libs/hidapi:$PWD/build/libs/libltc:$PWD/build/libs/clearlooks-newer:$PWD/build/libs/vst3:$PWD/build/libs/fst:$PATH"
# Ardour's own dev script sets the *_PATH variables for in-tree resources.
. gtk2_ardour/ardev_common.sh
exec build/gtk2_ardour/mastermix-*.exe "$@"
```
If `gtk2_ardour/ardev_common.sh` does not exist after the build, it is generated from `ardev_common.sh.in` by waf; check `build/gtk2_ardour/ardev_common.sh` and source that instead. If some DLL directory above does not exist, remove it from `PATH`; if the exe complains about a missing DLL, find it with `find build -name "<dll>"` and add its directory.

- [ ] **Step 2: Launch and capture**

Run in the background (Git Bash), no arguments so the splash is shown:
```
MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc 'tools/mastermix/run-dev.sh'
```

Wait 20 s, then capture the screen with PowerShell:
```powershell
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
[System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save("$env:TEMP\mastermix-shot1.png")
```
Read the PNG. Acceptance:
- Splash shows the M logo and "MASTERMIX".
- Session dialog / editor window title starts with `MasterMix`.
- Background is near-black, selection highlights and clocks are apple green.

Then create a new session (`Alt+N` in the session dialog, name `Test`, default folder), open the mixer (`Alt+M`), capture again. Open Help → About, capture, check "Ahmed Hadjadj" and the Ardour attribution appear. Close MasterMix cleanly (`Ctrl+Q`, discard).

- [ ] **Step 3: Fix what the screenshots reveal**

Typical issues and their fixes:
- Splash not found (`Cannot find splash screen image file` on stderr): the resources dir is not on `ARDOUR_DATA_PATH`; check Step 1's sourcing of `ardev_common.sh`.
- Theme not applied (grey UI): confirm `build/gtk2_ardour/../themes` contains `dark-mastermix.colors` and that `ARDOUR_CONFIG_PATH` doesn't point at an old `my-dark-*.colors`. Error text `no theme file was found; colors will be odd` means the search path is wrong.
- Text unreadable somewhere: adjust the offending base colour in `palette.py` (Task 3), re-run `python mastermix-branding/palette.py`, commit as `fix(theme): ...`.

- [ ] **Step 4: Commit**

```bash
git add tools/mastermix/run-dev.sh
git commit -m "build(msys2): in-tree launcher for MasterMix

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```
Copy the three screenshots to the user with SendUserFile at the end of the plan.

---

### Task 7 bis: French UI by default (added 2026-09-10 on user request)

**Files:**
- Modify: `libs/ardour/globals.cc` (`translate_by_default`: true on Windows)
- Modify: `gtk2_ardour/bundle_env_mingw.cc` (set `LANGUAGE=fr` when neither `LANGUAGE` nor `LANG` is set)
- Modify: `tools/mastermix/package-msys2.sh` (run `waf i18n_mo` + `waf install --destdir=build/stage`, ship `share/ardour9/locale`)
- Modify: `mastermix-branding/render.py` (no "basé sur Ardour" subtitle on the splash)

- [x] Step 1: `waf i18n_mo` compiles `po/fr.mo` for gtk2_ardour, libardour, gtkmm2ext, ytk.
- [x] Step 2: Windows locale dir is `<package dir>/share/ardour9/locale/<lang>/LC_MESSAGES/<domain>.mo`; in the dev tree the package dir is `build/gtk2_ardour`.
- [x] Step 3: translations were off by default on Windows (`translate_by_default = false`); flip it.
- [ ] Step 4: verify a French window title/labels in a screenshot (e.g. "Configuration Audio/MIDI").
- [ ] Step 5: commit.

---

### Task 7 ter: ASIO support in the PortAudio backend (added 2026-09-10 on user request)

**Files:**
- Create: `tools/mastermix/build-portaudio-asio.sh` (downloads Steinberg ASIO SDK zip, clones PortAudio v19.7.0, cmake static build with `PA_USE_ASIO=ON`, installs to `build/deps/prefix`)
- Modify: `tools/mastermix/build.sh` (uses that prefix via `PKG_CONFIG_PATH`, `LINKFLAGS=-L`, `--also-include`, `--also-libdir` when `pa_asio.h` exists)
- Modify: `tools/mastermix/setup-msys2.sh` (adds `cmake`, `ninja`)

- [x] Step 1: MSYS2 `libportaudio.dll` has WASAPI/WDM-KS but no `PaAsio_*` symbols.
- [x] Step 2: build static PortAudio with ASIO; `nm libportaudio.a | grep PaAsio_ShowControlPanel` non-empty.
- [x] Step 3: `waf configure` reports `Checking for header pa_asio.h : yes`.
- [ ] Step 4: rebuilt `portaudio_callback_backend.dll` contains `PaAsio_`; the Audio/MIDI dialog lists ASIO under "Pilote".
- [ ] Step 5: commit.

---

### Task 8: Run the upstream unit tests under MinGW

**Files:** none new. Uses `--test --run-tests` waf options.

- [ ] **Step 1: Reconfigure with tests in a separate build dir**

Run:
```
MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc 'PYTHON=/mingw64/bin/python3; $PYTHON ./waf configure --program-name=MasterMix --dist-target=mingw --with-backends=dummy --no-lrdf --test --out=build-tests 2>&1 | tail -5 && $PYTHON ./waf build --out=build-tests -j$(nproc) 2>&1 | tail -5 && $PYTHON ./waf build --out=build-tests --run-tests 2>&1 | tail -60'
```
Expected: `libs/pbd` and `libs/ardour` test runners report `OK (N tests)`. If the test targets fail to *compile* under MinGW, record the exact error in `tools/mastermix/README.md` under a "Known issues" heading and continue; do not patch test code in phase 1.

- [ ] **Step 2: Commit README note if needed**

```bash
git add tools/mastermix/README.md
git commit -m "docs(msys2): record unit-test status under MinGW"
```
(with attribution trailer)

---

### Task 9: Packaging and NSIS installer

**Files:**
- Create: `tools/mastermix/package-msys2.sh`
- Create: `tools/mastermix/mastermix.nsi.in`

**Interfaces:**
- Consumes: Task 6 build tree, `tools/x-win/nsis/FileAssociation.nsh` (reused), `gtk2_ardour/icons/MasterMix.ico`.
- Produces: `dist/MasterMix/` staging tree and `dist/MasterMix-9.8-Setup-x64.exe`.

Reference: `tools/x-win/package.sh` lines 120-260 list exactly which build artefacts are copied and where (`bin/`, `lib/ardour9/`, `share/ardour9/`). Mirror that layout but with `mastermix9` as the lowercase dirname, because `PROGRAM_NAME` changes `lwrcase_dirname` in `wscript` line 1666 (`'ardour' + MAJOR`) — check that line; if it hard-codes `ardour`, keep `ardour9` for the data dir (Ardour looks it up by that name) and only rename user-visible things.

- [ ] **Step 1: Write `package-msys2.sh`**

```bash
#!/bin/bash
# Copyright (C) 2026 Ahmed Hadjadj
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Stage a relocatable MasterMix tree from the MSYS2 build and wrap it in an
# NSIS installer. Run after tools/mastermix/build.sh, from MINGW64.
set -euo pipefail
cd "$(dirname "$0")/../.."
[ "${MSYSTEM:-}" = "MINGW64" ] || { echo "run from MINGW64" >&2; exit 1; }

PRODUCT=MasterMix
VERSION=$(git describe --tags --match '9.*' 2>/dev/null | sed 's/^v//' || echo 9.8)
VERSION=${VERSION%%-*}
DEST=dist/$PRODUCT
LOWER=$(grep -o "lwrcase_dirname = .*" build/c4che/_cache.py | head -1 | sed "s/.*'\(.*\)'/\1/")
LOWER=${LOWER:-ardour9}
EXE=$(ls build/gtk2_ardour/mastermix-*.exe | head -1)

rm -rf "$DEST"
mkdir -p "$DEST/bin" "$DEST/lib/$LOWER" "$DEST/share/$LOWER"

# 1. main binary and in-tree DLLs
cp "$EXE" "$DEST/bin/$PRODUCT.exe"
find build/libs -name '*.dll' -exec cp {} "$DEST/bin/" \;
for helper in build/libs/fst/ardour-vst-scanner.exe build/libs/fst/ardour-vst3-scanner.exe build/luasession/*-lua.exe; do
	[ -f "$helper" ] && cp "$helper" "$DEST/bin/"
done

# 2. backends, surfaces, panners, plugins (same layout as tools/x-win/package.sh)
mkdir -p "$DEST/lib/$LOWER"/{backends,surfaces,panners,LV2,vamp}
cp build/libs/backends/*/*.dll "$DEST/lib/$LOWER/backends/"
cp build/libs/surfaces/*/*.dll "$DEST/lib/$LOWER/surfaces/" 2>/dev/null || true
cp build/libs/panners/*/*.dll  "$DEST/lib/$LOWER/panners/"
cp -r build/libs/LV2/* "$DEST/lib/$LOWER/LV2/" 2>/dev/null || true
cp build/libs/vamp-plugins/*.dll "$DEST/lib/$LOWER/vamp/" 2>/dev/null || true

# 3. data: themes, resources, icons, scripts, templates, midi maps, patchfiles
cp -r gtk2_ardour/themes "$DEST/share/$LOWER/"
rm -f "$DEST/share/$LOWER/themes/"*-ardour.colors    # only MasterMix themes ship
mkdir -p "$DEST/share/$LOWER/resources"
cp gtk2_ardour/resources/${PRODUCT}-* "$DEST/share/$LOWER/resources/"
cp -r gtk2_ardour/icons "$DEST/share/$LOWER/"
cp gtk2_ardour/*.rc "$DEST/share/$LOWER/" 2>/dev/null || true
cp build/gtk2_ardour/*.rc "$DEST/share/$LOWER/" 2>/dev/null || true
cp gtk2_ardour/*.menus "$DEST/share/$LOWER/" 2>/dev/null || true
cp build/gtk2_ardour/*.menus "$DEST/share/$LOWER/" 2>/dev/null || true
cp gtk2_ardour/*.bindings "$DEST/share/$LOWER/" 2>/dev/null || true
cp build/gtk2_ardour/*.bindings "$DEST/share/$LOWER/" 2>/dev/null || true
cp gtk2_ardour/*.keys "$DEST/share/$LOWER/" 2>/dev/null || true
cp build/gtk2_ardour/*.keys "$DEST/share/$LOWER/" 2>/dev/null || true
cp system_config "$DEST/share/$LOWER/"
cp -r share/scripts "$DEST/share/$LOWER/"
cp -r share/templates "$DEST/share/$LOWER/" 2>/dev/null || true
cp -r share/midi_maps "$DEST/share/$LOWER/"
cp -r share/patchfiles "$DEST/share/$LOWER/"
cp -r share/plugin_metadata "$DEST/share/$LOWER/" 2>/dev/null || true
cp -r share/export "$DEST/share/$LOWER/"
cp -r share/mcp "$DEST/share/$LOWER/" 2>/dev/null || true
cp -r share/osc "$DEST/share/$LOWER/" 2>/dev/null || true
cp -r share/web_surfaces "$DEST/share/$LOWER/" 2>/dev/null || true
cp COPYING "$DEST/share/"

# 4. MinGW runtime DLLs the exe and libs depend on
ntldd -R "$DEST/bin/$PRODUCT.exe" "$DEST"/bin/*.dll "$DEST/lib/$LOWER"/*/*.dll 2>/dev/null \
	| grep -io '/mingw64/bin/[^ ]*\.dll' | sort -u | while read -r dll; do cp -n "$dll" "$DEST/bin/"; done

# 5. GTK/pango runtime data (fonts config, pixbuf loaders)
mkdir -p "$DEST/lib/gdk-pixbuf-2.0" "$DEST/etc/fonts"
cp -r /mingw64/lib/gdk-pixbuf-2.0/* "$DEST/lib/gdk-pixbuf-2.0/"
cp -r /mingw64/etc/fonts/* "$DEST/etc/fonts/"

# 6. installer
sed -e "s|@VERSION@|$VERSION|g" -e "s|@DEST@|$PWD/$DEST|g" -e "s|@LOWER@|$LOWER|g" \
	tools/mastermix/mastermix.nsi.in > dist/mastermix.nsi
makensis -V2 dist/mastermix.nsi
ls -la dist/*.exe
```

- [ ] **Step 2: Write `mastermix.nsi.in`**

```nsis
; Copyright (C) 2026 Ahmed Hadjadj
; SPDX-License-Identifier: GPL-2.0-or-later
Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!include "..\tools\x-win\nsis\FileAssociation.nsh"

Name "MasterMix @VERSION@"
OutFile "MasterMix-@VERSION@-Setup-x64.exe"
InstallDir "$PROGRAMFILES64\MasterMix"
InstallDirRegKey HKLM "Software\MasterMix" "Install_Dir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

VIProductVersion "@VERSION@.0.0"
VIAddVersionKey "ProductName" "MasterMix"
VIAddVersionKey "CompanyName" "Ahmed Hadjadj"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2026 Ahmed Hadjadj. Based on Ardour, (C) 1999-2026 Paul Davis. GPLv2+"
VIAddVersionKey "FileDescription" "MasterMix digital audio workstation"
VIAddVersionKey "FileVersion" "@VERSION@"

!define MUI_ICON "..\gtk2_ardour\icons\MasterMix.ico"
!define MUI_UNICON "..\gtk2_ardour\icons\MasterMix.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_TITLE "MasterMix est installé"
!define MUI_FINISHPAGE_TEXT "MasterMix est un logiciel libre (GPLv2+) dérivé d'Ardour.$\r$\nAuteur : Ahmed Hadjadj."
!define MUI_FINISHPAGE_RUN "$INSTDIR\bin\MasterMix.exe"

!insertmacro MUI_PAGE_LICENSE "..\COPYING"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "English"

Section "MasterMix" SecMain
	SectionIn RO
	SetOutPath "$INSTDIR"
	File /r "@DEST@\*.*"
	WriteRegStr HKLM "Software\MasterMix" "Install_Dir" "$INSTDIR"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterMix" "DisplayName" "MasterMix @VERSION@"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterMix" "Publisher" "Ahmed Hadjadj"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterMix" "DisplayIcon" "$INSTDIR\bin\MasterMix.exe"
	WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterMix" "UninstallString" '"$INSTDIR\Uninstall.exe"'
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterMix" "NoModify" 1
	WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterMix" "NoRepair" 1
	WriteUninstaller "$INSTDIR\Uninstall.exe"
	CreateDirectory "$SMPROGRAMS\MasterMix"
	CreateShortCut "$SMPROGRAMS\MasterMix\MasterMix.lnk" "$INSTDIR\bin\MasterMix.exe" "" "$INSTDIR\bin\MasterMix.exe" 0
	CreateShortCut "$DESKTOP\MasterMix.lnk" "$INSTDIR\bin\MasterMix.exe" "" "$INSTDIR\bin\MasterMix.exe" 0
	${registerExtension} "$INSTDIR\bin\MasterMix.exe" ".ardour" "MasterMix Session"
SectionEnd

Section "Uninstall"
	${unregisterExtension} ".ardour" "MasterMix Session"
	Delete "$SMPROGRAMS\MasterMix\MasterMix.lnk"
	RMDir "$SMPROGRAMS\MasterMix"
	Delete "$DESKTOP\MasterMix.lnk"
	RMDir /r "$INSTDIR"
	DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\MasterMix"
	DeleteRegKey HKLM "Software\MasterMix"
SectionEnd
```
Note the `..\` paths: `makensis` runs on `dist/mastermix.nsi`, so includes are relative to `dist/`.

- [ ] **Step 3: Run packaging**

Run:
```
MSYSTEM=MINGW64 CHERE_INVOKING=1 /c/msys64/usr/bin/bash.exe -lc 'tools/mastermix/package-msys2.sh' 2>&1 | tail -30
```
Expected: `dist/MasterMix-9.8-Setup-x64.exe` exists, size 100-300 MB.

- [ ] **Step 4: Verify the staged tree runs standalone**

Run: `dist/MasterMix/bin/MasterMix.exe` from PowerShell (double-click equivalent, *not* from an MSYS2 shell so `PATH` has no `/mingw64/bin`). Expected: splash, then session dialog; no "DLL not found" dialog. If a DLL is missing, the `ntldd` step missed it: add it to the copy list explicitly (`cp /mingw64/bin/<dll> "$DEST/bin/"`). Capture a screenshot as in Task 7.

- [ ] **Step 5: Install and uninstall test**

Run the installer silently: `dist/MasterMix-9.8-Setup-x64.exe /S` (needs admin; if UAC blocks, ask the user to run it). Expected: `C:\Program Files\MasterMix\bin\MasterMix.exe` exists and launches; then `"C:\Program Files\MasterMix\Uninstall.exe" /S` removes it.

- [ ] **Step 6: Add `dist/` to `.git/info/exclude`, commit**

```bash
echo dist/ >> .git/info/exclude
git add tools/mastermix/package-msys2.sh tools/mastermix/mastermix.nsi.in
git commit -m "build(msys2): staging and NSIS installer for MasterMix

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FSZRwZ3gs21UbN1jYFNKGA"
```

---

### Task 10: Final verification and hand-off

- [ ] **Step 1: Run the whole Python test suite**

Run: `python -m pytest mastermix-branding/tests -q`
Expected: all passed, 0 skipped.

- [ ] **Step 2: Check the branch history**

Run: `git log --oneline 9.8..HEAD`
Expected: one commit per task (plus `fix(mingw)` commits), all authored by Ahmed Hadjadj (`git log --format=%an 9.8..HEAD | sort -u`).

- [ ] **Step 3: Walk the spec §8 checklist**

Tick each item of "8. Vérification" in the spec against evidence (screenshots, log lines). Anything not met is reported to the user explicitly, with the error text.

- [ ] **Step 4: Send the user the screenshots and the installer path**

Use SendUserFile for the three screenshots from Task 7 and the Task 9 standalone screenshot. Report the path `dist/MasterMix-9.8-Setup-x64.exe`.
