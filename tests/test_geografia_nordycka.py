"""Kraje nordyckie w geografii „flanka” (decyzja właściciela 2026-11-03)."""
import re
from pathlib import Path

import pytest
import yaml

WZORCE = [re.compile(w, re.I) for w in yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "app" / "wskazniki.yaml").read_text(encoding="utf-8"))["geografia"]["flanka"]["wzorce"]]


def flanka(t):
    return any(w.search(t) for w in WZORCE)


@pytest.mark.parametrize("tekst", ["Rosyjskie drony nad Bornholmem", "Szwecja wzmacnia obronę", "Duńska armia w gotowości",
                                   "Sabotaż kabla w Danii", "Norweska policja", "Swedish navy", "Islandia", "Nordic defence",
                                   "Шведский флот", "Wizyta w Polsce"])
def test_flanka(tekst):
    assert flanka(tekst)


@pytest.mark.parametrize("tekst", ["Polecamy dania z dyni", "Pyszne danie", "Wybory w Brazylii"])
def test_poza_flanka(tekst):
    assert not flanka(tekst)
