import json

import linki


def test_domena():
    assert linki.domena("https://news.err.ee/x") == "err.ee"
    assert linki.domena("https://www.bbc.co.uk/news") == "bbc.co.uk"
    assert linki.domena("https://www.osw.waw.pl/pl/rss.xml") == "osw.waw.pl"


def test_ocen_link_odrzuca_podejrzane():
    dozw = {"osw.waw.pl"}
    assert linki.ocen_link("javascript:alert(1)", dozw, {}).startswith("schemat")
    assert linki.ocen_link("https://1.2.3.4/x", dozw, {}) == "adres IP zamiast domeny"
    assert linki.ocen_link("https://xn--80ak6aa92e.com/", dozw, {}) == "domena w punycode"
    assert linki.ocen_link("https://user@evil.com/", dozw, {}) == "dane logowania w adresie"
    assert linki.ocen_link("https://www.osw.waw.pl:8080/", dozw, {}).startswith("niestandardowy port")
    assert "spoza" in linki.ocen_link("https://evil.example/x", dozw, {})
    assert "zablokowana" in linki.ocen_link("https://www.osw.waw.pl/x", dozw, {"osw.waw.pl": {"powod": "test"}})


def test_ocen_link_przepuszcza_dobre():
    assert linki.ocen_link("https://www.osw.waw.pl/pl/publikacje/x", {"osw.waw.pl"}, {}) is None
    assert linki.ocen_link("", {"osw.waw.pl"}, {}) is None


def test_zabezpiecz_podmienia_na_strone_glowna():
    log = []
    w = linki.zabezpiecz({"id": "a1", "zrodlo": "osw-pl", "link": "https://phish.example/login"}, log)
    assert w["link"] == "https://www.osw.waw.pl/"
    assert "spoza" in w["link_odrzucony"] and len(log) == 1


def test_wyjatek_domeny_linkow():
    w = linki.zabezpiecz({"id": "b1", "zrodlo": "bbc-europe", "link": "https://www.bbc.co.uk/news/articles/x"}, [])
    assert "link_odrzucony" not in w


def test_zapisz_odrzucone_bez_powtorek(tmp_path):
    log = [{"id": "a1", "zrodlo": "x", "link": "l", "powod": "p"}]
    assert linki.zapisz_odrzucone(tmp_path, log) == 1
    assert linki.zapisz_odrzucone(tmp_path, log) == 0
    assert len((tmp_path / "linki_odrzucone.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_werdykt():
    r = {"malicious": 0, "suspicious": 0}
    assert linki.werdykt(r) == "czysta"
    assert linki.werdykt({**r, "malicious": 1}) == "do sprawdzenia"
    assert linki.werdykt({**r, "suspicious": 2}) == "do sprawdzenia"
    assert linki.werdykt({**r, "malicious": 2}) == "groźna"
    assert linki.werdykt({"blad": "HTTP 429"}) == "błąd"


def test_skanuj_blokuje_grozne(tmp_path, monkeypatch):
    monkeypatch.setattr(linki, "PLIK_BLOKADA", tmp_path / "blokada.yaml")
    monkeypatch.setattr(linki, "domeny_do_sprawdzenia", lambda *_: ["dobra.pl", "zla.example", "srednia.example"])
    odp = {"dobra.pl": (0, 0), "zla.example": (5, 1), "srednia.example": (1, 0)}

    def falszywy_vt(d, klucz):
        m, s = odp[d]
        return {"domena": d, "malicious": m, "suspicious": s, "harmless": 60, "reputacja": 0, "silniki": ["X"] if m else []}

    monkeypatch.setattr(linki, "raport_vt", falszywy_vt)
    w = linki.skanuj(None, tmp_path / "wynik.md", "klucz", przerwa=0)
    assert w["nowe_blokady"] == ["zla.example"]
    assert w["licz"] == {"czysta": 1, "do sprawdzenia": 1, "groźna": 1, "błąd": 0}
    assert "zla.example" in linki.wczytaj_blokade()
    assert "srednia.example" in (tmp_path / "wynik.md").read_text(encoding="utf-8")
