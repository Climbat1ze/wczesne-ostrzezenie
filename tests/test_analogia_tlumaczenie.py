"""Analogia 2021/22 z weryfikacją sensu, rozpoznanie strony po rosyjsku, dotłumaczanie zaległych trafień (wersja 2.0)."""
import datetime as dt
import json

import pytest

import intencja
import ostrzezenie as o
import tlumacz

S = o.Slownik()


@pytest.mark.parametrize("t,oczekiwana", [
    ("Военные из 12 стран Европы отработают в Польше развертывание контингента в Украине", "wlasna"),
    ("Тысячи европейских военных проведут учения в Польше по развертыванию в Украине", "wlasna"),
    ("Россия перебрасывает войска к границе Литвы", "przeciwnik"),
])
def test_strona_po_rosyjsku(t, oczekiwana):
    assert intencja.strona(t) == oczekiwana


def test_europejskie_cwiczenia_w_polsce_to_nie_cwiczenia_rosji():
    t = "Тысячи европейских военных проведут учения в Польше по развертыванию в Украине в случае заключения мира с Россией"
    assert "cwiczenia" not in S.kategorie(t)


def test_kazdy_kamien_ma_kryterium_odpowiednika():
    assert all(a.get("odpowiednik") for a in S.analogia)


def _wpis(i, grupa, kat="ostrzezenia_sojusznikow"):
    return {"id": i, "zrodlo": "x", "grupa": grupa, "wydawca": grupa, "tytul": f"t{i}", "link": "", "geo": "flanka",
            "kategorie": [kat], "data": "2026-11-04T10:00"}


def test_analogia_liczy_tylko_potwierdzone(monkeypatch):
    nr = next(n for n, a in enumerate(S.analogia) if a["kategoria"] == "ostrzezenia_sojusznikow")
    monkeypatch.setattr(intencja, "_PAMIEC_AN", {
        f"{nr}:a": {"odpowiednik": False, "pewnosc": 0.9, "powod": "rosyjskie oskarżenie Polski, to pretekst"},
        f"{nr}:b": {"odpowiednik": False, "pewnosc": 0.8, "powod": "ogólna wypowiedź Putina"}})
    zr = {"x": {"id": "x", "status": "aktywne", "wiarygodnosc": "A"}}
    koniec = dt.datetime(2026, 11, 4, 12, tzinfo=dt.timezone.utc)
    w = o.analogia([_wpis("a", "g1"), _wpis("b", "g2")], zr, S, koniec, weryfikuj=False)[nr]
    assert w["trafienie"] is False and w["odrzucone"] == 2 and w["grup"] == 0


def test_analogia_bez_modelu_liczy_jak_dawniej(monkeypatch):
    nr = next(n for n, a in enumerate(S.analogia) if a["kategoria"] == "ostrzezenia_sojusznikow")
    monkeypatch.setattr(intencja, "_PAMIEC_AN", {})
    zr = {"x": {"id": "x", "status": "aktywne", "wiarygodnosc": "A"}}
    koniec = dt.datetime(2026, 11, 4, 12, tzinfo=dt.timezone.utc)
    w = o.analogia([_wpis("a", "g1"), _wpis("b", "g2")], zr, S, koniec, weryfikuj=False)[nr]
    assert w["trafienie"] is True and w["niezweryfikowane"] == 2


def test_dotlumacz_z_pamieci(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_WYLACZ", "1")
    pw, pp = tmp_path / "wpisy.jsonl", tmp_path / "tl.json"
    pw.write_text(json.dumps({"id": "1", "zrodlo": "bbc-ru", "tytul": "Учения в Польше", "lead": ""}) + "\n"
                  + json.dumps({"id": "2", "zrodlo": "pl", "tytul": "Ćwiczenia", "lead": ""}) + "\n", encoding="utf-8")
    pp.write_text(json.dumps({"1": {"t": "Ćwiczenia w Polsce", "l": ""}}), encoding="utf-8")
    n = tlumacz.dotlumacz_trafienia(pw, {"bbc-ru": {"jezyk": "ru"}, "pl": {"jezyk": "pl"}}, pp)
    w = [json.loads(l) for l in pw.read_text(encoding="utf-8").splitlines()]
    assert n == 1 and w[0]["tytul"] == "Ćwiczenia w Polsce" and w[0]["oryginal"] == "Учения в Польше" and w[0]["jezyk"] == "ru"
    assert "oryginal" not in w[1]
