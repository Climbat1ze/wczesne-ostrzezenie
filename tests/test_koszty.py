import koszty


def test_budzet_przydziela_do_limitu_i_wysyla_jeden_mail(dane_tmp, monkeypatch):
    monkeypatch.setenv("CLAUDE_BUDZET_DZIENNY", "5")
    assert koszty.przydziel(3) == 3
    assert koszty.przydziel(4) == 2          # zostały 2
    assert koszty.przydziel(1) == 0          # wyczerpany
    assert koszty.zuzycie_dzis() == 5
    maile_o_budzecie = [m for m in dane_tmp if "Budżet" in m["temat"]]
    assert len(maile_o_budzecie) == 1        # jeden mail na dobę, nie przy każdym wywołaniu


def test_wylacznik_blokuje_wszystkie_wywolania(dane_tmp, monkeypatch):
    monkeypatch.setenv("CLAUDE_WYLACZ", "1")
    assert koszty.przydziel(10) == 0
    import tlumacz
    assert tlumacz.tryb() is None


def test_limit_alarmow_i_kolejka(dane_tmp, monkeypatch):
    monkeypatch.setenv("ALARMY_DZIENNIE", "2")
    assert koszty.wyslij_alarm("A1", "t", "<body></body>", "spietrzenie") == "wyslany"
    assert koszty.wyslij_alarm("A2", "t", "<body></body>", "trend") == "wyslany"
    assert koszty.wyslij_alarm("A3", "t", "<body></body>", "krytyczny") == "w_kolejce"
    assert koszty.alarmy_dzis() == 2
    assert [m["temat"] for m in dane_tmp] == ["A1", "A2"]
    assert len(koszty._kolejka()) == 1
    # następnego dnia limit się zeruje: kolejka dokleja się do pierwszego alarmu
    monkeypatch.setattr(koszty, "_dzis", lambda: "2099-01-01")
    assert koszty.wyslij_alarm("B1", "t", "<body></body>", "trend") == "wyslany"
    assert "A3" in dane_tmp[-1]["tekst"]
    assert koszty._kolejka() == []


def test_kolejka_wysylana_zbiorczo_o_godzinie_raportu(dane_tmp, monkeypatch):
    monkeypatch.setenv("ALARMY_DZIENNIE", "0")
    koszty.wyslij_alarm("X", "t", "<body></body>", "trend")
    monkeypatch.setenv("ALARMY_DZIENNIE", "3")
    assert koszty.oproznij_kolejke(godzina_raportu=False) is False
    assert koszty.oproznij_kolejke(godzina_raportu=True) is True
    assert dane_tmp[-1]["temat"].startswith("Zbiorczo")


def test_raport_7dni(dane_tmp):
    koszty.przydziel(2)
    koszty.zapisz_mail("raport", "tydzien")
    koszty.zapisz_przebieg(120.0, 60, 63)
    r = koszty.raport_7dni()
    assert r["claude_7d"] == 2 and r["maile_7d"] == 1 and r["przebiegi_7d"] == 1 and r["czas_max_s"] == 120.0


def test_tlumaczenie_nie_rusza_rezerwy(dane_tmp, monkeypatch):
    monkeypatch.setenv("CLAUDE_BUDZET_DZIENNY", "20")
    monkeypatch.setenv("CLAUDE_REZERWA", "5")
    assert koszty.przydziel(100, "tlumaczenie") == 15     # do limitu minus rezerwa
    assert koszty.przydziel(1, "tlumaczenie") == 0
    assert koszty.przydziel(3) == 3                       # intencja i analogia mają zapas
    assert koszty.przydziel(5) == 2
    assert len([m for m in dane_tmp if "Budżet" in m["temat"]]) == 1   # mail dopiero przy wyczerpaniu puli ogólnej


def test_zgloszenia_poza_budzetem_dziennym(dane_tmp, monkeypatch):
    monkeypatch.setenv("CLAUDE_BUDZET_DZIENNY", "3")
    assert koszty.przydziel(3) == 3
    assert koszty.przydziel(1) == 0
    assert koszty.przydziel(1, "zgloszenia") == 1         # skan na zlecenie działa mimo wyczerpanego budżetu
    assert koszty.zuzycie_dzis() == 3
    monkeypatch.setenv("CLAUDE_WYLACZ", "1")
    assert koszty.przydziel(1, "zgloszenia") == 0         # wyłącznik obowiązuje zawsze


def test_nieznana_pula(dane_tmp):
    import pytest
    with pytest.raises(ValueError):
        koszty.przydziel(1, "inna")
