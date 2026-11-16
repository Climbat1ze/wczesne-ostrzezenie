"""Oszczędność zapytań do Claude (2.1.0): wspólne paczki tłumaczenia, analogia co 6 h, źródła rzadkie."""
import datetime as dt

import intencja
import tlumacz
import utrzymanie


def _wpisy(prefix, n, data="2026-11-16T10:00"):
    return [{"id": f"{prefix}{i}", "tytul": f"{prefix} {i}", "lead": "", "data": data} for i in range(n)]


def _udawany_model(monkeypatch, zapytania):
    monkeypatch.setattr(tlumacz, "dostepne", lambda: True)
    monkeypatch.setattr(tlumacz, "_stan", {"wywolan": 0, "przetlumaczono": 0, "bledy": 0, "pominieto": None,
                                           "odlozono": 0, "budzet": False})

    def paczka(elementy):
        zapytania.append([e["j"] for e in elementy])
        tlumacz._stan["wywolan"] += 1
        return {i: {"t": f"PL {e['t']}", "l": ""} for i, e in enumerate(elementy)}
    monkeypatch.setattr(tlumacz, "_paczka", paczka)


def test_kanaly_w_roznych_jezykach_ida_jednym_zapytaniem(dane_tmp, monkeypatch):
    zapytania = []
    _udawany_model(monkeypatch, zapytania)
    lt, lv, et, en = _wpisy("lt", 5), _wpisy("lv", 7), _wpisy("et", 3), _wpisy("en", 4)
    pamiec = {}
    tlumacz.przetlumacz_kanaly([(lt, "lt", True), (lv, "lv", True), (et, "et", False), (en, "en", True)], pamiec)
    assert len(zapytania) == 1                       # dawniej 3 zapytania (po jednym na kanał)
    assert sorted(set(zapytania[0])) == ["et", "lt", "lv"]
    assert lt[0]["tytul"] == "PL lt 0" and lt[0]["oryginal"] == "lt 0" and lt[0]["jezyk"] == "lt"
    assert en[0]["tytul"] == "en 0" and "oryginal" not in en[0]
    assert len(pamiec) == 15


def test_limit_zapytan_na_przebieg_i_pierwszenstwo_zrodel_liczonych(dane_tmp, monkeypatch):
    zapytania = []
    _udawany_model(monkeypatch, zapytania)
    proba = _wpisy("proba", tlumacz.PACZKA * tlumacz.MAKS_ZAPYTAN, data="2026-11-16T12:00")  # nowsze, ale na próbie
    aktywne = _wpisy("akt", 10, data="2026-11-16T09:00")
    pamiec = {}
    tlumacz.przetlumacz_kanaly([(proba, "lv", False), (aktywne, "lt", True)], pamiec)
    assert len(zapytania) == tlumacz.MAKS_ZAPYTAN
    assert all(w["id"] in pamiec for w in aktywne)   # źródła liczone do indeksu nie czekają
    assert tlumacz._stan["odlozono"] == 10


def test_pamiec_oszczedza_zapytanie(dane_tmp, monkeypatch):
    zapytania = []
    _udawany_model(monkeypatch, zapytania)
    w = _wpisy("lt", 3)
    pamiec = {x["id"]: {"t": "znane", "l": ""} for x in w}
    tlumacz.przetlumacz_kanaly([(w, "lt", True)], pamiec)
    assert zapytania == [] and w[0]["tytul"] == "znane"


def test_analogia_najwyzej_raz_na_6_godzin(monkeypatch):
    teraz = dt.datetime(2026, 11, 16, 12, tzinfo=dt.timezone.utc)
    znane = {"0:a": {"ts": (teraz - dt.timedelta(hours=2)).isoformat(timespec="minutes")}}
    assert intencja._za_wczesnie_na_analogie(znane, teraz) is True
    znane = {"0:a": {"ts": (teraz - dt.timedelta(hours=7)).isoformat(timespec="minutes")}}
    assert intencja._za_wczesnie_na_analogie(znane, teraz) is False
    assert intencja._za_wczesnie_na_analogie({}, teraz) is False

    monkeypatch.setattr(intencja, "_PAMIEC_AN", {"0:a": {"ts": (teraz - dt.timedelta(hours=1)).isoformat(timespec="minutes")}})
    wolano = []
    import claude_cli
    monkeypatch.setattr(claude_cli, "dostepny", lambda: True)
    monkeypatch.setattr(claude_cli, "zapytaj", lambda *a, **k: wolano.append(1) or (True, "[]"))
    wpis = {"id": "b", "tytul": "t", "wydawca": "x"}
    assert intencja.weryfikuj_analogie([(0, {"co": "c"}, wpis)], teraz) == 0
    assert wolano == []


def _zrodlo(**k):
    return {"id": "us", "nazwa": "US", "url": "https://example.invalid/rss", "status": "aktywne", "wiarygodnosc": "A", **k}


def test_zrodlo_rzadkie_nie_jest_martwe_przez_cisze():
    teraz = dt.datetime(2026, 11, 16, 12, tzinfo=dt.timezone.utc)
    stat = {"us": {"dni": {}, "ostatnio_ok": "2026-11-16T11:00", "najnowszy": "2026-10-23", "blad_od": None}}

    def bez_sieci(url, timeout=15):
        return None, "brak"
    zwykle = utrzymanie.przeglad([_zrodlo()], {}, stat, teraz, bez_sieci, None, zastosuj=False)
    assert [z["na"] for z in zwykle["zmiany"]] == ["obserwacja"]
    rzadkie = utrzymanie.przeglad([_zrodlo(rzadki=True)], {}, stat, teraz, bez_sieci, None, zastosuj=False)
    assert rzadkie["zmiany"] == []
    # błąd kanału nadal się liczy
    stat["us"]["blad_od"] = "2026-11-01"
    rzadkie_z_bledem = utrzymanie.przeglad([_zrodlo(rzadki=True)], {}, stat, teraz, bez_sieci, None, zastosuj=False)
    assert [z["na"] for z in rzadkie_z_bledem["zmiany"]] == ["obserwacja"]
