"""Tłumaczenie nagłówków z kanałów w językach lokalnych (łotewski, litewski, estoński, fiński, rosyjski) na polski.

Model: Haiku (zadanie mechaniczne: wynik sprawdzalny, tani).
Tylko subskrypcja Claude (Max): CLAUDE_CODE_OAUTH_TOKEN z `claude setup-token`, wywołanie `claude -p` (Claude Code CLI).
Bez dodatkowych opłat, zużywa limity subskrypcji. Płatne API wyłączone (decyzja 2026-11-02).
Każdy nagłówek tłumaczony raz: pamięć podręczna w dane/tlumaczenia.json (14 dni).
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
NAZWY = {"lv": "łotewskiego", "lt": "litewskiego", "et": "estońskiego", "fi": "fińskiego", "ru": "rosyjskiego"}
PACZKA = 40  # nagłówków w jednym zapytaniu
MAKS_ZAPYTAN = 16  # na jeden przebieg workflow (ok. 640 nagłówków)
ROWNOLEGLE = 4

SYSTEM = (
    "Tłumaczysz nagłówki i leady wiadomości na język polski dla polskiego czytelnika śledzącego bezpieczeństwo w regionie. "
    "Tłumacz wiernie i rzeczowo, bez dodawania ocen i bez wygładzania. Zachowaj nazwy własne, liczby i cytaty. "
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


def _paczka_cli(wejscie: str, jezyk: str) -> dict[int, dict]:
    """Claude Code CLI na subskrypcji, bez narzędzi (claude_cli.zapytaj)."""
    import claude_cli  # noqa: E402
    ok, wynik = claude_cli.zapytaj(SYSTEM, f"Przetłumacz z {NAZWY.get(jezyk, jezyk)} na polski:\n{wejscie}", model="haiku")
    _stan["wywolan"] += 1
    if not ok:
        print("Tłumaczenie (subskrypcja): błąd,", wynik)
        _stan["bledy"] += 1
        return {}
    return _parsuj(wynik)


def _paczka(elementy: list[dict], jezyk: str) -> dict[int, dict]:
    wejscie = "\n".join(json.dumps({"i": i, "t": e["t"], "l": e["l"][:220]}, ensure_ascii=False) for i, e in enumerate(elementy))
    return _paczka_cli(wejscie, jezyk)


def przetlumacz(wpisy: list[dict], jezyk: str, pamiec: dict) -> None:
    """Podmienia w wpisach tytuł i lead na polskie; oryginał zostaje w polu 'oryginal'. Modyfikuje w miejscu."""
    if jezyk in JEZYKI_BEZ_TLUMACZENIA or not wpisy:
        return
    brak = [w for w in wpisy if w["id"] not in pamiec]
    if brak and not dostepne():
        import koszty  # noqa: E402
        _stan["pominieto"] = "wyłącznik CLAUDE_WYLACZ=1" if koszty.wylaczone() else "brak CLAUDE_CODE_OAUTH_TOKEN"
    elif brak:
        # Limit na przebieg: pierwsze uruchomienie ma ok. 1000 zaległych nagłówków, a workflow ma 10 minut.
        # Najnowsze idą pierwsze; reszta w kolejnych godzinach (pamięć podręczna pamięta, co już jest).
        brak.sort(key=lambda w: w.get("data", ""), reverse=True)
        wolne = max(0, MAKS_ZAPYTAN - _stan["wywolan"])
        paczki = [brak[i:i + PACZKA] for i in range(0, len(brak), PACZKA)][:wolne]
        import koszty  # noqa: E402
        przyznane = koszty.przydziel(len(paczki))  # dzienny budżet zapytań (CLAUDE_BUDZET_DZIENNY)
        if przyznane < len(paczki):
            _stan["budzet"] = True
        paczki = paczki[:przyznane]
        if len(paczki) * PACZKA < len(brak):
            _stan["odlozono"] += len(brak) - len(paczki) * PACZKA
        with ThreadPoolExecutor(max_workers=ROWNOLEGLE) as ex:
            wyniki = list(ex.map(lambda c: _paczka([{"t": w["tytul"], "l": w.get("lead", "")} for w in c], jezyk), paczki))
        for czesc, wynik in zip(paczki, wyniki):
            for j, w in enumerate(czesc):
                if j in wynik:
                    pamiec[w["id"]] = {"t": wynik[j]["t"], "l": wynik[j].get("l", ""), "d": dt.date.today().isoformat()}
                    _stan["przetlumaczono"] += 1
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
