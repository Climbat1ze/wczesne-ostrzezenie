import strona


def _z(id, kraj, jezyk="en", status="aktywne"):
    return {"id": id, "kraj": kraj, "jezyk": jezyk, "status": status, "wiarygodnosc": "B", "nazwa": id}


def test_grupy_region_kraj_i_tlumaczenie():
    zr = [_z("svt", "SE", "sv"), _z("pap", "PL", "pl"), _z("lrt", "LT", "lt"), _z("err", "EE", "en"), _z("x", "QA")]
    w = strona.wiersze_zrodel_grupami(zr, lambda z, reg: f"<tr data-status>{z['id']}|{reg}</tr>")
    tekst = "\n".join(w)
    # kolejność regionów: Polska, Bałtyk, Nordycy, ..., Pozostałe
    assert tekst.index("Polska") < tekst.index("Kraje bałtyckie") < tekst.index("Kraje nordyckie") < tekst.index("Pozostałe")
    assert "tłumaczone na polski: szwedzki" in tekst
    assert "tłumaczone na polski: litewski" in tekst
    # region z jednym krajem: jeden nagłówek, bez osobnego nagłówka kraju
    assert 'data-naglowek="k:PL"' not in tekst and 'data-naglowek="r:Polska"' in tekst
    assert 'data-naglowek="k:LT"' in tekst and 'data-naglowek="k:EE"' in tekst
    assert "svt|Kraje nordyckie" in tekst


def test_odmiana():
    assert strona._opis_grupy([_z("a", "PL")]).startswith("1 źródło")
    assert strona._opis_grupy([_z(str(i), "PL") for i in range(3)]).startswith("3 źródła")
    assert strona._opis_grupy([_z(str(i), "PL") for i in range(12)]).startswith("12 źródeł")
    assert strona._opis_grupy([_z(str(i), "PL") for i in range(22)]).startswith("22 źródła")
