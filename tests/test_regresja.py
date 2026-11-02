"""Testy regresji klasyfikacji na zamrożonych, prawdziwych nagłówkach (tests/dane/przypadki.jsonl).

- Przypadki poprawne: wynik słownika musi się równać oczekiwanym kategoriom (zmiana = regresja).
- Znane pomyłki (znana_pomylka=true): oczekujemy poprawnej kategorii, ale test jest oznaczony xfail.
  Gdy poprawka słownika je naprawi, pytest pokaże XPASS: wtedy zmień flagę na false.
"""
import json
from pathlib import Path

import pytest

import ostrzezenie as o

PLIK = Path(__file__).parent / "dane" / "przypadki.jsonl"
PRZYPADKI = [json.loads(l) for l in PLIK.read_text(encoding="utf-8").splitlines() if l.strip()]
SLOWNIK = o.Slownik()


def _kategorie(p):
    return sorted(SLOWNIK.kategorie(f"{p['tytul']}. {p.get('lead', '')}"))


@pytest.mark.parametrize("p", [p for p in PRZYPADKI if not p["znana_pomylka"]], ids=lambda p: p["id"])
def test_poprawne_bez_regresji(p):
    assert _kategorie(p) == p["oczekiwane"], p["tytul"]


@pytest.mark.parametrize("p", [p for p in PRZYPADKI if p["znana_pomylka"]], ids=lambda p: p["id"])
@pytest.mark.xfail(reason="znana pomyłka słownika", strict=False)
def test_znane_pomylki(p):
    assert _kategorie(p) == p["oczekiwane"], p["uwaga"]


def test_zestaw_ma_co_najmniej_50_przypadkow():
    assert len(PRZYPADKI) >= 50
