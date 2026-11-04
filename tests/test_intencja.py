"""Kontrola strony i intencji (wersja 2.0): działania strony własnej nie podnoszą WW."""
import datetime as dt

import pytest

import intencja
import ostrzezenie as o

S = o.Slownik()


@pytest.mark.parametrize("t,oczekiwana", [
    ("Poland deploys special forces to Russian border", "wlasna"),
    ("Polska wysyła wojsko na granicę z Białorusią", "wlasna"),
    ("Urzędnicy szkolą się z obsługi broni palnej", "wlasna"),
    ("Poland mobilizes police and army at the border with Kaliningrad", "wlasna"),
    ("Russia is massing troops near the Lithuanian border", "przeciwnik"),
    ("Polish forces observe Russian troops massing near border", "przeciwnik"),
    ("Lithuanian intelligence: Belarus redeploys brigades to the Polish border", "przeciwnik"),
    ("Pogoda na weekend: deszcz i wiatr", "nieznana"),
])
def test_strona(t, oczekiwana):
    assert intencja.strona(t) == oczekiwana


def test_wlasna_mobilizacja_nie_liczy_sie_do_gotowosci():
    t = "Poland mobilizes police and army at the border with Kaliningrad, following warnings about sabotage"
    assert "gotowosc" not in S.kategorie(t)
    assert "gotowosc" in S.wlasne(t)


def test_mobilizacja_przeciwnika_sie_liczy():
    assert "gotowosc" in S.kategorie("Russia announces mobilization of reservists in Kaliningrad")


def test_werdykt_modelu_zdejmuje_tylko_przy_pewnosci(monkeypatch):
    monkeypatch.setattr(intencja, "_PAMIEC", {
        "a": {"strona": "wlasna", "kategorie_ok": [], "pewnosc": 0.9, "powod": "ćwiczenia własne"},
        "b": {"strona": "wlasna", "kategorie_ok": [], "pewnosc": 0.5, "powod": "niepewne"}})
    wa = intencja.zastosuj({"id": "a", "kategorie": ["hybryda", "deeskalacja"], "krytyczne": ["mobilizacja"]}, S.kat)
    wb = intencja.zastosuj({"id": "b", "kategorie": ["hybryda"]}, S.kat)
    assert wa["kategorie"] == ["deeskalacja"]       # waga ujemna zostaje
    assert wa["krytyczne"] == ["mobilizacja"]       # sygnałów krytycznych model nie wycisza
    assert wb["kategorie"] == ["hybryda"]           # pewność < 0,7: bez zmian


def test_kandydaci_tylko_alarmowe_z_flanki(monkeypatch):
    monkeypatch.setattr(intencja, "_PAMIEC", {})
    teraz = dt.datetime(2026, 11, 4, 12, tzinfo=dt.timezone.utc)
    zr = {"x": {"status": "aktywne", "wiarygodnosc": "B"}, "y": {"status": "aktywne", "wiarygodnosc": "E"}}
    wpisy = [{"id": "1", "zrodlo": "x", "geo": "flanka", "kategorie": ["wojska_granica"], "data": "2026-11-04T10:00"},
             {"id": "2", "zrodlo": "y", "geo": "flanka", "kategorie": ["wojska_granica"], "data": "2026-11-04T10:00"},
             {"id": "3", "zrodlo": "x", "geo": "reszta", "kategorie": ["wojska_granica"], "data": "2026-11-04T10:00"},
             {"id": "4", "zrodlo": "x", "geo": "flanka", "kategorie": ["wojska_granica"], "data": "2026-10-20T10:00"}]
    assert [w["id"] for w in intencja.kandydaci(wpisy, zr, S.kat, teraz)] == ["1"]


def test_bez_tokenu_brak_wywolan(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    monkeypatch.setattr(intencja, "_PAMIEC", {})
    teraz = dt.datetime.now(dt.timezone.utc)
    w = [{"id": "1", "zrodlo": "x", "geo": "flanka", "kategorie": ["wojska_granica"], "data": teraz.isoformat()}]
    assert intencja.weryfikuj(w, {"x": {"status": "aktywne", "wiarygodnosc": "A"}}, S.kat, teraz) == 0
