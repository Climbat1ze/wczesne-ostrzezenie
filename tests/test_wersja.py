"""Wersjonowanie: plik app/WERSJA, CHANGELOG.md zaczyna się od tej wersji, rejestr CR ją zna."""
import re
from pathlib import Path

import wersja

ROOT = Path(__file__).resolve().parent.parent


def test_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", wersja.WERSJA)


def test_changelog_zgodny_z_wersja():
    pierwsza = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    assert pierwsza and pierwsza.group(1) == wersja.WERSJA, "podnieś app/WERSJA albo dopisz wersję na górze CHANGELOG.md"


def test_rejestr_cr_wskazuje_wersje():
    assert wersja.WERSJA in (ROOT / "docs" / "change_requests.md").read_text(encoding="utf-8")
