import json
import urllib.parse

import samouczenie


def test_mnozniki_z_potwierdzalnosci():
    m = samouczenie.policz_mnozniki({
        "dobre": {"trafien_30d": 12, "potwierdzalnosc": 0.9},
        "slabe": {"trafien_30d": 10, "potwierdzalnosc": 0.0},
        "srednie": {"trafien_30d": 9, "potwierdzalnosc": 0.5},
        "malo_danych": {"trafien_30d": 3, "potwierdzalnosc": 0.0},
    })
    assert m["dobre"]["mnoznik"] == 1.2 and m["slabe"]["mnoznik"] == 0.6
    assert m["srednie"]["mnoznik"] == 1.0 and m["malo_danych"]["mnoznik"] == 1.0


def test_link_oceny_ma_etykiete_i_id():
    url = samouczenie.link_oceny("ocena-pomylka", "Ocena: pomyłka · X", "wpis:abcdef123456")
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert q["labels"] == ["ocena-pomylka"] and q["body"] == ["wpis:abcdef123456"]


def test_wczytaj_oceny_dopisuje_przypadki(tmp_path, monkeypatch):
    import ostrzezenie as o
    monkeypatch.setattr(samouczenie, "DANE", tmp_path)
    monkeypatch.setattr(samouczenie, "TESTY_DANE", tmp_path / "testy")
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    issues = {"ocena-trafny": [{"number": 1, "body": "wpis:aaaaaaaaaaaa", "title": "t"}],
              "ocena-pomylka": [{"number": 2, "body": "wpis:bbbbbbbbbbbb", "title": "t"},
                                {"number": 3, "body": "alarm:cccccccccccc", "title": "Ocena alarmu"}]}
    monkeypatch.setattr(samouczenie, "_pobierz_issue", lambda et, tok: issues[et])
    wpisy = {"aaaaaaaaaaaa": {"id": "aaaaaaaaaaaa", "zrodlo": "bbc", "tytul": "Cyberatak na ministerstwo", "lead": ""},
             "bbbbbbbbbbbb": {"id": "bbbbbbbbbbbb", "zrodlo": "rp", "tytul": "Smog spowił Delhi, wojska przy granicy", "lead": ""}}
    w = samouczenie.wczytaj_oceny(wpisy, o.Slownik())
    assert w == {"nowe_wpisy": 2, "nowe_alarmy": 1, "blad": None}
    przypadki = [json.loads(l) for l in (tmp_path / "testy" / "przypadki.jsonl").read_text().splitlines()]
    assert przypadki[1]["oczekiwane"] == [] and przypadki[1]["znana_pomylka"] is True
    # drugi przebieg niczego nie dubluje
    assert samouczenie.wczytaj_oceny(wpisy, o.Slownik())["nowe_wpisy"] == 0


def test_mnozniki_czekaja_na_30_dni_statystyk(tmp_path, monkeypatch):
    monkeypatch.setattr(samouczenie, "DANE", tmp_path)
    (tmp_path / "statystyki_zrodel.json").write_text('{"lrt-en": {"dni": {"2099-01-01": {}}}}')
    nowe, zmiany = samouczenie.zapisz_mnozniki({"lrt-en": {"trafien_30d": 9, "potwierdzalnosc": 0.0}})
    assert nowe["lrt-en"]["mnoznik"] == 1.0 and "30 dniach" in zmiany[0]
