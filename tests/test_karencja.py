import datetime as dt

import ostrzezenie as o


def _wpis(zrodlo, grupa, teraz):
    return {"zrodlo": zrodlo, "grupa": grupa, "geo": "flanka", "krytyczne": ["Mobilizacja"], "tytul": "x", "link": "l",
            "wydawca": grupa, "data": teraz.isoformat(timespec="minutes")}


def test_nowe_zrodlo_w_karencji_nie_liczy_sie_do_sygnalu_krytycznego():
    teraz = dt.datetime(2026, 12, 10, 12, tzinfo=dt.timezone.utc)
    zrodla = {
        "stare": {"status": "aktywne", "wiarygodnosc": "A", "dodano": "2026-11-02"},
        "nowe": {"status": "aktywne", "wiarygodnosc": "A", "dodano": "2026-12-01"},
        "drugie": {"status": "aktywne", "wiarygodnosc": "B", "dodano": "2026-11-02"},
    }
    tylko_z_nowym = [_wpis("stare", "g1", teraz), _wpis("nowe", "g2", teraz)]
    assert o.sygnaly_krytyczne(tylko_z_nowym, zrodla, teraz) == []
    dwa_stare = [_wpis("stare", "g1", teraz), _wpis("drugie", "g3", teraz)]
    assert len(o.sygnaly_krytyczne(dwa_stare, zrodla, teraz)) == 1


def test_karencja_konczy_sie_po_30_dniach():
    z = {"dodano": "2026-12-01"}
    assert o.w_karencji(z, dt.date(2026, 12, 30))
    assert not o.w_karencji(z, dt.date(2026, 12, 31))
    assert not o.w_karencji({"dodano": "2026-11-02"}, dt.date(2026, 11, 3))   # pierwotny rejestr bez karencji
    assert not o.w_karencji({}, dt.date(2026, 11, 3))


def test_kazde_zrodlo_ma_date_dodania():
    assert all(z.get("dodano") for z in o.wczytaj_zrodla())
