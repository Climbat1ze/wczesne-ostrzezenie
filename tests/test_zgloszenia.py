"""Zgłoszenia: formularz issue, dopasowanie słów, bezpieczeństwo linku, limity, analiza wsteczna, scalanie historii."""
import json

import pytest

import zgloszenia as zg

CIALO = """### Słowa kluczowe

urzędnicy szkolenie broń

### Link

_No response_

### Co usłyszałeś lub przeczytałeś

Kolega mówi, że administracja szkoli się z bronią palną.
"""


def test_parsuj_formularz_slowa():
    z = zg.parsuj_issue("[skan] urzędnicy", CIALO)
    assert z == {"tryb": "slowa", "slowa": "urzędnicy szkolenie broń", "link": "",
                 "kontekst": "Kolega mówi, że administracja szkoli się z bronią palną."}


def test_parsuj_link_bez_formularza():
    z = zg.parsuj_issue("sprawdź to", "Przeczytałem https://example.com/a?b=1 i nie wiem")
    assert z["tryb"] == "link" and z["link"] == "https://example.com/a?b=1"


def test_parsuj_sam_tytul():
    assert zg.parsuj_issue("[skan] wojsko granica", "")["slowa"] == "wojsko granica"


def test_dopasowanie_od_poczatku_slowa():
    w = [zg.wzorzec("granica")]
    assert zg.pasuje("Wojsko przy granicy z Rosją", w)
    assert not zg.pasuje("Szokujące nagranie z drogi", w)
    assert not zg.pasuje("Sejm chce ograniczyć rekompensaty", w)


def test_wszystkie_slowa_musza_pasowac():
    w = [zg.wzorzec("wojsko Białoruś")]
    assert zg.pasuje("Białoruś przerzuca wojsko", w)
    assert not zg.pasuje("Wojsko na ćwiczeniach w Niemczech", w)


@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "file:///etc/passwd", "http://user:pw@example.com/",
                                 "http://localhost/admin", "https://example.com:8443/"])
def test_niebezpieczne_adresy_odrzucone(url):
    assert zg.ocen_adres(url)


def test_wyciagnij_tresc():
    h = ('<html><head><title>T</title><meta property="og:title" content="Tytuł OG">'
         '<meta name="description" content="Opis"></head><body><script>alert(1)</script>'
         '<article><p>' + "Akapit treści artykułu, wystarczająco długi, żeby się liczył. " * 2 + '</p></article></body></html>')
    x = zg.wyciagnij(h)
    assert x["tytul"] == "Tytuł OG" and x["opis"] == "Opis" and "alert" not in x["tekst"] and "Akapit" in x["tekst"]


def test_limity(tmp_path, monkeypatch):
    monkeypatch.setattr(zg, "PLIK_LIMITY", tmp_path / "limity.json")
    monkeypatch.setenv("ZGLOSZENIA_NA_OSOBE", "2")
    monkeypatch.setenv("ZGLOSZENIA_DZIENNIE", "3")
    assert zg.sprawdz_limit("ala", False, "2026-11-04")[0]
    assert zg.sprawdz_limit("ala", False, "2026-11-04")[0]
    assert not zg.sprawdz_limit("ala", False, "2026-11-04")[0]      # 3. od tej samej osoby
    assert zg.sprawdz_limit("wlasciciel", True, "2026-11-04")[0]    # właściciel bez limitu na osobę
    assert not zg.sprawdz_limit("ola", False, "2026-11-04")[0]      # limit dzienny razem
    assert zg.sprawdz_limit("ola", False, "2026-11-05")[0]          # nowa doba


def test_brier_i_trafnosc():
    assert zg.brier(0.9, "falsz") == 0.81
    assert zg.brier(0.5, "prawda") == 0.25
    assert zg.brier(0.7, "nierozstrzygniete") is None
    assert zg.trafny_z_reguly("niepotwierdzone", "falsz") is True
    assert zg.trafny_z_reguly("potwierdzone", "falsz") is False
    assert zg.trafny_z_reguly("za_malo_danych", "prawda") is None


def test_walidacja_odpowiedzi_modelu():
    a = zg.waliduj({"werdykt": "cos_dziwnego", "pewnosc": "1.7", "znaczenie": "kosmiczne",
                    "hipotezy": [{"h": "H1", "obali_ja": "X", "stan": "utrzymana"}, "śmieć"]}, "teza")
    assert a["werdykt"] == "za_malo_danych" and a["pewnosc"] == 1.0 and a["znaczenie"] is None
    assert len(a["hipotezy"]) == 1 and a["teza"] == "teza"


def test_do_retro_po_7_i_30_dniach(tmp_path, monkeypatch):
    import datetime as dt
    monkeypatch.setattr(zg, "PLIK", tmp_path / "zgloszenia.jsonl")
    t = dt.datetime(2026, 12, 10, tzinfo=dt.timezone.utc)
    rek = [{"id": "A", "ts": "2026-12-01T10:00+00:00", "analiza": {"werdykt": "niepotwierdzone"}, "retro": {}},
           {"id": "B", "ts": "2026-11-01T10:00+00:00", "analiza": {"werdykt": "potwierdzone"}, "retro": {"7d": {}}},
           {"id": "C", "ts": "2026-11-01T10:00+00:00", "analiza": {"werdykt": "bez_oceny"}, "retro": {}}]
    (tmp_path / "zgloszenia.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rek), encoding="utf-8")
    assert [(r["id"], e) for r, e in zg.do_retro(t)] == [("A", "7d"), ("B", "30d")]


def test_scal_nie_gubi_rownoleglych(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    (b / "zgloszenia.jsonl").write_text(json.dumps({"id": "ZG-1", "ts": "1", "retro": {"7d": {"wynik": "prawda"}}}) + "\n")
    (a / "zgloszenia.jsonl").write_text(json.dumps({"id": "ZG-1", "ts": "1", "retro": {}}) + "\n"
                                        + json.dumps({"id": "ZG-2", "ts": "2", "retro": {}}) + "\n")
    zg.scal(a, b)
    wynik = {r["id"]: r for r in map(json.loads, (b / "zgloszenia.jsonl").read_text().splitlines())}
    assert set(wynik) == {"ZG-1", "ZG-2"} and wynik["ZG-1"]["retro"]["7d"]["wynik"] == "prawda"


def test_id_z_numerem_issue():
    assert zg.nowe_id("2026-11-04", 12) == "ZG-20261104-12"


def test_zaufany(monkeypatch):
    monkeypatch.setenv("ZGLOSZENIA_ZAUFANI", "Patryk-X, @inny")
    assert zg.zaufany("patryk-x") and zg.zaufany("INNY")
    assert not zg.zaufany("obcy")
    monkeypatch.delenv("ZGLOSZENIA_ZAUFANI")
    assert not zg.zaufany("patryk-x")
