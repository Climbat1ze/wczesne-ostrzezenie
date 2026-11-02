"""Samouczenie bez ruszania progów alarmów i wag kategorii.

1. Wiarygodność źródeł z danych: mnożnik 0,6–1,2 do oceny A–F, liczony co tydzień z potwierdzalności
   (jak często alarmujące wiadomości źródła potwierdzają w 48–72 h inne wiarygodne redakcje). Działa dopiero po 30 dniach
   statystyk i przy min. 8 alarmowych trafieniach źródła w 30 dniach; wcześniej mnożnik = 1,0. Oceny A–F zostają bez zmian.
2. Oceny właściciela: w poniedziałkowym raporcie administracyjnym przy każdym alarmie i każdej pomyłce z oceny trafności
   są linki „trafny” / „pomyłka”, które otwierają gotowe issue z etykietą ocena-trafny albo ocena-pomylka.
   Poniedziałkowy przebieg czyta te issue (GITHUB_TOKEN, tylko odczyt) i dopisuje oceny wpisów do tests/dane/
   jako nowe przypadki regresji; oceny alarmów trafiają do tests/dane/oceny_wlasciciela.jsonl.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent
DANE = APP / "dane"
TESTY_DANE = APP.parent / "tests" / "dane"
MIN_TRAFIEN = 8
ZAKRES = (0.6, 1.2)
REPO_DOMYSLNE = "Climbat1ze/wczesne-ostrzezenie"
ETYKIETY = {"ocena-trafny": "trafny", "ocena-pomylka": "pomylka"}


def _czytaj(p: Path, domyslnie):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return domyslnie


# ---------------------------------------------------------------- 1. wiarygodność z danych

def policz_mnozniki(jakosc_zrodel: dict) -> dict:
    """Mnożnik = 0,6 + 0,8 × potwierdzalność, obcięty do 0,6–1,2; 1,0 przy zbyt małej liczbie trafień."""
    wynik = {}
    for zid, j in jakosc_zrodel.items():
        traf, potw = j.get("trafien_30d", 0), j.get("potwierdzalnosc")
        if traf >= MIN_TRAFIEN and potw is not None:
            m = round(min(ZAKRES[1], max(ZAKRES[0], 0.6 + 0.8 * potw)), 2)
        else:
            m = 1.0
        wynik[zid] = {"mnoznik": m, "potwierdzalnosc": potw, "trafien_30d": traf}
    return wynik


KARENCJA_STATYSTYK_DNI = 30


def wiek_statystyk() -> int:
    stat = _czytaj(DANE / "statystyki_zrodel.json", {})
    dni = [d for v in stat.values() for d in v.get("dni", {})]
    if not dni:
        return 0
    return (dt.date.today() - dt.date.fromisoformat(min(dni))).days


def zapisz_mnozniki(jakosc_zrodel: dict) -> tuple[dict, list[str]]:
    p = DANE / "wiarygodnosc_dyn.json"
    stare = _czytaj(p, {}).get("zrodla", {})
    wiek = wiek_statystyk()
    if wiek < KARENCJA_STATYSTYK_DNI:
        # Za krótka historia: potwierdzalność jest zbyt niepewna (zwłaszcza między językami), mnożniki zostają 1,0.
        nowe = {zid: {"mnoznik": 1.0, "potwierdzalnosc": j.get("potwierdzalnosc"), "trafien_30d": j.get("trafien_30d", 0)}
                for zid, j in jakosc_zrodel.items()}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "zrodla": nowe},
                                ensure_ascii=False, indent=1), encoding="utf-8")
        return nowe, [f"Statystyki mają {wiek} dni; mnożniki ruszą po {KARENCJA_STATYSTYK_DNI} dniach (do tego czasu 1,0)."]
    nowe = policz_mnozniki(jakosc_zrodel)
    zmiany = [f"{zid}: {stare.get(zid, {}).get('mnoznik', 1.0)} → {v['mnoznik']} (potwierdzalność "
              f"{(v['potwierdzalnosc'] or 0) * 100:.0f}%, trafień {v['trafien_30d']})"
              for zid, v in sorted(nowe.items()) if v["mnoznik"] != stare.get(zid, {}).get("mnoznik", 1.0)]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "zrodla": nowe},
                            ensure_ascii=False, indent=1), encoding="utf-8")
    return nowe, zmiany


_CACHE: dict | None = None


def mnoznik(zid: str) -> float:
    global _CACHE
    if _CACHE is None:
        _CACHE = _czytaj(DANE / "wiarygodnosc_dyn.json", {}).get("zrodla", {})
    return float(_CACHE.get(zid, {}).get("mnoznik", 1.0))


def odswiez_cache():
    global _CACHE
    _CACHE = None


# ---------------------------------------------------------------- 2. oceny właściciela

def id_alarmu(ts: str, temat: str) -> str:
    return hashlib.sha1(f"{ts}|{temat}".encode()).hexdigest()[:12]


def repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or REPO_DOMYSLNE


def link_oceny(etykieta: str, tytul: str, cialo: str) -> str:
    q = urllib.parse.urlencode({"title": tytul[:120], "labels": etykieta, "body": cialo})
    return f"https://github.com/{repo()}/issues/new?{q}"


def alarmy_tygodnia(dni: int = 7) -> list[dict]:
    p = DANE / "alarmy.jsonl"
    if not p.exists():
        return []
    granica = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=dni)).isoformat()
    return [a for a in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()) if a.get("ts", "") >= granica]


def linie_ocen(bledne_z_oceny: list[dict]) -> list:
    """Linie do raportu administracyjnego z linkami (poczta.Html, bo zawierają <a>)."""
    import poczta  # noqa: E402
    from html import escape as e  # noqa: E402
    styl = 'style="color:#4dff91"'

    def para(tytul, cialo):
        return (f'<a href="{e(link_oceny("ocena-trafny", "Ocena: trafny · " + tytul, cialo))}" {styl}>trafny</a> / '
                f'<a href="{e(link_oceny("ocena-pomylka", "Ocena: pomyłka · " + tytul, cialo))}" {styl}>pomyłka</a>')
    linie = []
    for a in alarmy_tygodnia():
        linie.append(poczta.Html(f"Alarm {e(a['ts'][:16])} UTC · {e(a['temat'])} · {para(a['temat'], 'alarm:' + a['id'])}"))
    for b in bledne_z_oceny[:10]:
        linie.append(poczta.Html(f"Wpis „{e(b['tytul'][:90])}” → {e(', '.join(b['kategorie']))} · {para(b['tytul'][:60], 'wpis:' + b['id'])}"))
    if not linie:
        linie.append("Brak alarmów i ocenionych pomyłek w tym tygodniu.")
    linie.append("Kliknięcie otwiera gotowe issue: wystarczy je zapisać. Oceny trafiają do testów w następny poniedziałek.")
    return linie


def _pobierz_issue(etykieta: str, token: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo()}/issues?labels={etykieta}&state=all&per_page=100"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                               "User-Agent": "wczesne-ostrzezenie"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def wczytaj_oceny(wpisy_po_id: dict, slownik) -> dict:
    """Czyta issue z ocenami i dopisuje nowe przypadki. Zwraca {'nowe_wpisy': n, 'nowe_alarmy': n, 'blad': str|None}."""
    token = os.environ.get("GITHUB_TOKEN")
    wynik = {"nowe_wpisy": 0, "nowe_alarmy": 0, "blad": None}
    if not token:
        wynik["blad"] = "brak GITHUB_TOKEN"
        return wynik
    przetworzone_p = DANE / "oceny_przetworzone.json"
    przetworzone = set(_czytaj(przetworzone_p, []))
    przypadki_p = TESTY_DANE / "przypadki.jsonl"
    oceny_p = TESTY_DANE / "oceny_wlasciciela.jsonl"
    TESTY_DANE.mkdir(parents=True, exist_ok=True)
    istniejace = set()
    if przypadki_p.exists():
        istniejace = {json.loads(l)["id"] for l in przypadki_p.read_text(encoding="utf-8").splitlines() if l.strip()}
    for etykieta, ocena in ETYKIETY.items():
        try:
            issues = _pobierz_issue(etykieta, token)
        except Exception as ex:  # noqa: BLE001  — brak dostępu do API nie może zatrzymać przebiegu
            wynik["blad"] = type(ex).__name__
            continue
        for i in issues:
            klucz = f"{i['number']}"
            if klucz in przetworzone or "pull_request" in i:
                continue
            m = re.search(r"\b(wpis|alarm):([0-9a-f]{8,20})\b", i.get("body") or "")
            if not m:
                continue
            rodzaj, ident = m.groups()
            if rodzaj == "wpis" and ident in wpisy_po_id and ident not in istniejace:
                w = wpisy_po_id[ident]
                akt = sorted(slownik.kategorie(f"{w['tytul']}. {w.get('lead', '')}"))
                ocz = akt if ocena == "trafny" else []
                with open(przypadki_p, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"id": ident, "zrodlo": w["zrodlo"], "tytul": w["tytul"], "lead": w.get("lead", ""),
                                        "aktualne": akt, "geo": slownik.geografia(f"{w['tytul']}. {w.get('lead', '')}"),
                                        "oczekiwane": ocz, "znana_pomylka": akt != ocz,
                                        "uwaga": f"ocena właściciela, issue #{i['number']}"}, ensure_ascii=False) + "\n")
                istniejace.add(ident)
                wynik["nowe_wpisy"] += 1
            elif rodzaj == "alarm":
                with open(oceny_p, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"alarm": ident, "ocena": ocena, "issue": i["number"],
                                        "tytul": (i.get("title") or "")[:160]}, ensure_ascii=False) + "\n")
                wynik["nowe_alarmy"] += 1
            przetworzone.add(klucz)
    przetworzone_p.write_text(json.dumps(sorted(przetworzone), ensure_ascii=False), encoding="utf-8")
    return wynik
