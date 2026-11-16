"""Tłumaczenie nagłówków z kanałów w językach lokalnych (łotewski, litewski, estoński, fiński, rosyjski) na polski.

Model: Haiku (zadanie mechaniczne: wynik sprawdzalny, tani).
Tylko subskrypcja Claude (Max): CLAUDE_CODE_OAUTH_TOKEN z `claude setup-token`, wywołanie `claude -p` (Claude Code CLI).
Bez dodatkowych opłat, zużywa limity subskrypcji. Płatne API wyłączone (decyzja 2026-11-02).
Każdy nagłówek tłumaczony raz: pamięć podręczna w dane/tlumaczenia.json (14 dni).
Oszczędność zapytań (2.1.0): nagłówki ze wszystkich kanałów i języków jednego przebiegu idą wspólnymi paczkami po 60
(wcześniej osobne zapytanie dla każdego kanału, średnio 10 nagłówków na zapytanie). Najpierw źródła liczone do indeksu
(aktywne, monitoring), potem źródła na próbie; nadmiar czeka na kolejny przebieg.
Bez tokenu albo przy błędzie: zostaje oryginał, aplikacja działa dalej.
Nagłówki z RSS to treść z zewnątrz: model nie dostaje żadnych narzędzi, tylko tłumaczy.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor

JEZYKI_BEZ_TLUMACZENIA = {"pl", "en"}
NAZWY = {"lv": "łotewskiego", "lt": "litewskiego", "et": "estońskiego", "fi": "fińskiego", "ru": "rosyjskiego",
         "sv": "szwedzkiego", "no": "norweskiego", "da": "duńskiego"}
PACZKA = 60  # nagłówków w jednym zapytaniu (różne języki razem)
MAKS_ZAPYTAN = 4  # na jeden przebieg workflow (240 nagłówków; zwykle przybywa ok. 40 na godzinę)
ROWNOLEGLE = 2

SYSTEM = (
    "Tłumaczysz nagłówki i leady wiadomości na język polski dla polskiego czytelnika śledzącego bezpieczeństwo w regionie. "
    "Tłumacz wiernie i rzeczowo, bez dodawania ocen i bez wygładzania. Zachowaj nazwy własne, liczby i cytaty. "
    "Każda pozycja ma pole j: kod języka oryginału (lv, lt, et, fi, ru, sv, no, da). "
    "Zwróć wyłącznie tablicę JSON, bez komentarza: [{\"i\": numer, \"t\": \"tytuł po polsku\", \"l\": \"lead po polsku\"}]."
)

_stan = {"wywolan": 0, "przetlumaczono": 0, "bledy": 0, "pominieto": None, "odlozono": 0, "budzet": False}


def tryb() -> str | None:
    import koszty  # noqa: E402
    if koszty.wylaczone():
        return None
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") and shutil.which("claude"):
        return "subskrypcja"
    return None


def dostepne() -> bool:
    return tryb() is not None


def _parsuj(tekst: str) -> dict[int, dict]:
    m = re.search(r"\[.*\]", tekst, re.S)
    try:
        dane = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        _stan["bledy"] += 1
        return {}
    return {int(d["i"]): d for d in dane if isinstance(d, dict) and "i" in d and d.get("t")}


def _paczka_cli(wejscie: str) -> dict[int, dict]:
    """Claude Code CLI na subskrypcji, bez narzędzi (claude_cli.zapytaj)."""
    import claude_cli  # noqa: E402
    ok, wynik = claude_cli.zapytaj(SYSTEM, f"Przetłumacz na polski:\n{wejscie}", model="haiku")
    _stan["wywolan"] += 1
    if not ok:
        print("Tłumaczenie (subskrypcja): błąd,", wynik)
        _stan["bledy"] += 1
        return {}
    return _parsuj(wynik)


def _paczka(elementy: list[dict]) -> dict[int, dict]:
    """elementy: {"t": tytuł, "l": lead, "j": kod języka}. Jedno zapytanie na paczkę, języki mogą być różne."""
    wejscie = "\n".join(json.dumps({"i": i, "j": e["j"], "t": e["t"], "l": e["l"][:220]}, ensure_ascii=False)
                        for i, e in enumerate(elementy))
    return _paczka_cli(wejscie)


def _tlumacz_brakujace(brak: list[tuple[dict, str]], pamiec: dict, maks_zapytan: int) -> int:
    """brak: (wpis, język) w kolejności ważności. Wspólne paczki po PACZKA, najwyżej `maks_zapytan` zapytań.

    Zapisuje tłumaczenia w `pamiec`. Zwraca liczbę zapytań. Nadmiar liczy się jako odłożony na kolejny przebieg.
    """
    import koszty  # noqa: E402
    paczki = [brak[i:i + PACZKA] for i in range(0, len(brak), PACZKA)][:max(0, maks_zapytan)]
    przyznane = koszty.przydziel(len(paczki), "tlumaczenie") if paczki else 0  # dzienny budżet (CLAUDE_BUDZET_DZIENNY)
    if przyznane < len(paczki):
        _stan["budzet"] = True
    paczki = paczki[:przyznane]
    _stan["odlozono"] += max(0, len(brak) - sum(len(c) for c in paczki))
    if not paczki:
        return 0
    with ThreadPoolExecutor(max_workers=ROWNOLEGLE) as ex:
        wyniki = list(ex.map(lambda c: _paczka([{"t": w["tytul"], "l": w.get("lead", ""), "j": j} for w, j in c]), paczki))
    for czesc, wynik in zip(paczki, wyniki):
        for k, (w, _) in enumerate(czesc):
            if k in wynik:
                pamiec[w["id"]] = {"t": wynik[k]["t"], "l": wynik[k].get("l", ""), "d": dt.date.today().isoformat()}
                _stan["przetlumaczono"] += 1
    return len(paczki)


def przetlumacz_kanaly(kanaly: list[tuple[list[dict], str, bool]], pamiec: dict) -> None:
    """Tłumaczy nagłówki wszystkich kanałów przebiegu naraz. kanaly: (wpisy, język, czy_priorytet).

    Priorytetowe (źródła liczone do indeksu) idą pierwsze, w każdej grupie najnowsze pierwsze. Modyfikuje wpisy w miejscu.
    """
    brak, widziane = [], set()
    for wpisy, jezyk, prio in kanaly:
        if jezyk in JEZYKI_BEZ_TLUMACZENIA:
            continue
        for w in wpisy:
            if w["id"] not in pamiec and w["id"] not in widziane:
                widziane.add(w["id"])
                brak.append((w, jezyk, prio))
    if brak and not dostepne():
        import koszty  # noqa: E402
        _stan["pominieto"] = "wyłącznik CLAUDE_WYLACZ=1" if koszty.wylaczone() else "brak CLAUDE_CODE_OAUTH_TOKEN"
    elif brak:
        brak.sort(key=lambda x: (x[2], x[0].get("data", "")), reverse=True)
        _tlumacz_brakujace([(w, j) for w, j, _ in brak], pamiec, MAKS_ZAPYTAN - _stan["wywolan"])
    for wpisy, jezyk, _ in kanaly:
        if jezyk not in JEZYKI_BEZ_TLUMACZENIA:
            _naloz(wpisy, jezyk, pamiec)


def przetlumacz(wpisy: list[dict], jezyk: str, pamiec: dict) -> None:
    """Podmienia w wpisach tytuł i lead na polskie; oryginał zostaje w polu 'oryginal'. Modyfikuje w miejscu."""
    if jezyk in JEZYKI_BEZ_TLUMACZENIA or not wpisy:
        return
    przetlumacz_kanaly([(wpisy, jezyk, True)], pamiec)


def _naloz(wpisy: list[dict], jezyk: str, pamiec: dict) -> None:
    for w in wpisy:
        p = pamiec.get(w["id"])
        if not p:
            continue
        w["oryginal"] = w["tytul"]
        w["jezyk"] = jezyk
        w["tytul"] = p["t"]
        w["lead"] = p.get("l", "")[:300]
        w["_tekst"] = f"{p['t']}. {p.get('l', '')} || {w['oryginal']}"  # oryginał zostaje: rosyjskie wzorce słownika nadal działają


def przytnij(pamiec: dict, dni: int = 14) -> dict:
    granica = (dt.date.today() - dt.timedelta(days=dni)).isoformat()
    return {k: v for k, v in pamiec.items() if v.get("d", "") >= granica}


def raport() -> str:
    if _stan["pominieto"]:
        return f"Tłumaczenie: pominięte ({_stan['pominieto']}), nagłówki zostają w oryginale"
    return (f"Tłumaczenie ({tryb() or 'brak'}): {_stan['przetlumaczono']} nagłówków w {_stan['wywolan']} zapytaniach, "
            f"błędy: {_stan['bledy']}, odłożone na kolejne przebiegi: {_stan['odlozono']}"
            + (", dzienny budżet wyczerpany" if _stan["budzet"] else ""))


MAKS_DOTLUMACZ = 1  # zapytań na przebieg dla zaległych trafień (to one trafiają na pulpit i do maili)


def dotlumacz_trafienia(plik_wpisy, zrodla_idx: dict, plik_pamieci) -> int:
    """Wpisy z trafieniem wskaźników zapisane bez tłumaczenia (limit przebiegu, brak budżetu) dostają je później.

    Najpierw z pamięci tłumaczeń, potem nowe zapytania (najwyżej 1 po 60 nagłówków, języki razem, najnowsze pierwsze). Wynik zapisany
    w dane/wpisy.jsonl, więc tłumaczenie zostaje na 90 dni, a nie tylko na 14 dni pamięci. Zwraca liczbę uzupełnionych.
    """
    from pathlib import Path  # noqa: E402
    plik_wpisy, plik_pamieci = Path(plik_wpisy), Path(plik_pamieci)
    if not plik_wpisy.exists():
        return 0
    wpisy = [json.loads(l) for l in plik_wpisy.read_text(encoding="utf-8").splitlines() if l.strip()]
    try:
        pamiec = json.loads(plik_pamieci.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pamiec = {}

    def jezyk(w):
        return (zrodla_idx.get(w.get("zrodlo")) or {}).get("jezyk", "pl")
    brak = [w for w in wpisy if not w.get("oryginal") and jezyk(w) not in JEZYKI_BEZ_TLUMACZENIA]
    if not brak:
        return 0
    do_zapytania = sorted((w for w in brak if w["id"] not in pamiec), key=lambda w: w.get("data", ""), reverse=True)
    if do_zapytania and dostepne():
        _tlumacz_brakujace([(w, jezyk(w)) for w in do_zapytania], pamiec, MAKS_DOTLUMACZ)
        plik_pamieci.write_text(json.dumps(pamiec, ensure_ascii=False), encoding="utf-8")
    n = 0
    for w in brak:
        p = pamiec.get(w["id"])
        if p:
            w["oryginal"], w["jezyk"] = w["tytul"], jezyk(w)
            w["tytul"], w["lead"] = p["t"], p.get("l", "")[:300]
            n += 1
    if n:
        plik_wpisy.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n" for w in wpisy), encoding="utf-8")
        print(f"Tłumaczenie: uzupełniono {n} zaległych trafień (z {len(brak)} bez tłumaczenia)")
    return n
