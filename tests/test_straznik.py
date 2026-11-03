import copy
from pathlib import Path

import yaml

import straznik

BAZA = yaml.safe_load((Path(__file__).resolve().parent.parent / "app" / "wskazniki.yaml").read_text(encoding="utf-8"))


def test_zmiana_wzorca_dozwolona():
    d = copy.deepcopy(BAZA)
    d["kategorie"]["deeskalacja"]["wzorce"].append(r"\bnowy wzorzec")
    d["kategorie"]["deeskalacja"]["wykluczenia"] = [r"\bkoniec rozejmu"]
    assert straznik.roznice(BAZA, d) == []


def test_zmiana_wagi_lub_progu_odrzucona():
    d = copy.deepcopy(BAZA)
    d["kategorie"]["hybryda"]["waga"] = 5
    assert any(r.startswith("wagi") for r in straznik.roznice(BAZA, d))
    d = copy.deepcopy(BAZA)
    d["progi"][1]["od"] = 35
    assert any(r.startswith("progi") for r in straznik.roznice(BAZA, d))


def test_wykluczenie_zdejmuje_kategorie(monkeypatch):
    import ostrzezenie as o
    s = o.Slownik()
    assert "deeskalacja" in s.kategorie("Koniec rozejmu w Ołeszkach")
    import re
    s.wyk["deeskalacja"] = [re.compile(r"\bkoniec rozejmu", re.I)]
    assert "deeskalacja" not in s.kategorie("Koniec rozejmu w Ołeszkach")
