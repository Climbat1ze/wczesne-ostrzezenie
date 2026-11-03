import jakosc


def test_incydent_po_trzech_slabych_przebiegach_i_jeden_mail(tmp_path, monkeypatch):
    monkeypatch.setattr(jakosc, "DANE", tmp_path)
    assert jakosc.zapisz_zdrowie(60, 63, 0, None)["nowy_incydent"] is None
    assert jakosc.zapisz_zdrowie(40, 63, 0, None)["nowy_incydent"] is None
    assert jakosc.zapisz_zdrowie(40, 63, 0, None)["nowy_incydent"] is None
    assert "80%" in jakosc.zapisz_zdrowie(40, 63, 0, None)["nowy_incydent"]  # trzeci słaby z rzędu: incydent
    w = jakosc.zapisz_zdrowie(40, 63, 0, None)
    assert w["nowy_incydent"] is None                                          # ten sam incydent: bez drugiego maila
    s = w["stan"]
    assert s["incydent"] is not None
    w = jakosc.zapisz_zdrowie(63, 63, 0, None)
    assert w["koniec_incydentu"] is True


def test_incydent_przy_bledach_tlumaczenia(tmp_path, monkeypatch):
    monkeypatch.setattr(jakosc, "DANE", tmp_path)
    wyniki = [jakosc.zapisz_zdrowie(63, 63, 2, None)["nowy_incydent"] for _ in range(3)]
    assert wyniki[:2] == [None, None] and "tłumaczenie" in wyniki[2]


def test_ocena_trafnosci_pomijana_bez_tokenu(tmp_path, monkeypatch):
    monkeypatch.setattr(jakosc, "DANE", tmp_path)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    import datetime as dt
    teraz = dt.datetime.now(dt.timezone.utc).isoformat()
    wpisy = [{"id": "a", "tytul": "x", "kategorie": ["cyber"], "data": teraz}]
    assert jakosc.ocena_trafnosci(wpisy, {"cyber": {"nazwa": "Cyber"}}) is None
