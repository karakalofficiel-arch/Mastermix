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
import importlib
import re
from pathlib import Path

po_protools = importlib.import_module("po-protools")

ROOT = Path(__file__).resolve().parents[3]

SAMPLE = (
    'msgid ""\n'
    'msgstr ""\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    "\n"
    "#: editor.cc:1\n"
    'msgid "Regions"\n'
    'msgstr "Régions"\n'
    "\n"
    'msgid "Mixer"\n'
    'msgstr "Console de mixage"\n'
    "\n"
    'msgid "Untouched"\n'
    'msgstr "Intact"\n'
)


def test_apply_replaces_only_listed_msgstr():
    out = po_protools.apply(SAMPLE, {"Regions": "Clips", "Mixer": "Mixage"}, {})
    assert 'msgid "Regions"\nmsgstr "Clips"\n' in out
    assert 'msgid "Mixer"\nmsgstr "Mixage"\n' in out
    assert 'msgid "Untouched"\nmsgstr "Intact"\n' in out


def test_apply_is_idempotent():
    once = po_protools.apply(SAMPLE, {"Regions": "Clips"}, {"INSERTS A-E": "INSERTS A-E"})
    twice = po_protools.apply(once, {"Regions": "Clips"}, {"INSERTS A-E": "INSERTS A-E"})
    assert once == twice


def test_apply_appends_missing_additions_once():
    out = po_protools.apply(SAMPLE, {}, {"Start": "Début"})
    assert out.count('msgid "Start"\n') == 1
    assert 'msgid "Start"\nmsgstr "Début"\n' in out


def test_apply_updates_an_addition_already_present():
    once = po_protools.apply(SAMPLE, {}, {"Start": "Début"})
    out = po_protools.apply(once, {}, {"Start": "Commencement"})
    assert out.count('msgid "Start"\n') == 1
    assert 'msgid "Start"\nmsgstr "Commencement"\n' in out


def test_apply_keeps_crlf_line_endings():
    out = po_protools.apply(SAMPLE.replace("\n", "\r\n"), {"Regions": "Clips"}, {})
    assert "\r\n" in out and 'msgstr "Clips"\r\n' in out


def test_apply_leaves_the_header_entry_alone():
    out = po_protools.apply(SAMPLE, {"": "broken"}, {})
    assert out.startswith('msgid ""\nmsgstr ""\n')


def test_every_substitution_msgid_exists_upstream():
    for rel, table in po_protools.SUBSTITUTIONS.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        ids = set(re.findall(r'^msgid "(.*)"\r?$', text, re.M))
        missing = set(table) - ids
        assert not missing, f"{rel}: unknown msgid {missing}"
