"""Źródła same się utrzymują: cotygodniowy przegląd rejestru według stałych reguł.

Co robi automatycznie (każda zmiana trafia do notatki źródła, do dane/zmiany_zrodel.jsonl i do maila):
  1. Martwy lub nieaktualny kanał (błąd od 7 dni albo najnowszy wpis starszy niż 14 dni):
     szuka nowego adresu RSS w tej samej domenie; jeśli znajdzie działający, podmienia adres.
     Jeśli nie znajdzie: aktywne -> obserwacja; po 30 dniach martwy -> zablokowane.
  2. Źródło na próbie (obserwacja) po 30 dniach: awans do aktywnych albo blokada (krzykliwość, potwierdzalność).
     Za mało tytułów do oceny: próba przedłużona o 30 dni.
  3. Aktywne źródło, które zaczęło krzyczeć albo przestało być potwierdzane: z powrotem na próbę.
     Ta reguła działa dopiero po 30 dniach od startu statystyk (wcześniej liczby są za małe).

Czego NIGDY nie robi sam: zmiana oceny A–F, odblokowanie źródła, zmiana statusu „monitoring”
(poza blokadą martwego kanału), dodanie nowego źródła. To decyzje właściciela projektu.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from urllib.parse import urljoin, urlparse

import feedparser

REGULY = {
    "martwy_dni": 7,            # tyle dni błędu, zanim uznamy kanał za martwy
    "nieaktualny_dni": 14,      # najnowszy wpis starszy niż tyle dni = kanał nieaktualny
    "martwy_blokada_dni": 30,   # martwy tak długo -> zablokowane
    "proba_dni": 30,            # długość próby (obserwacja)
    "krzyk_max": 0.15,          # maks. odsetek krzykliwych tytułów
    "potw_min": 0.30,           # min. potwierdzalność alarmowych wiadomości
    "min_tytulow": 20,          # mniej tytułów w 30 dni = za mało danych do oceny
    "min_trafien_ocena": 5,     # od tylu alarmowych trafień liczymy potwierdzalność przy awansie
    "min_trafien_degradacja": 10,
    "min_tytulow_degradacja": 50,
    "karencja_dni": 30,         # degradacja aktywnych dopiero po tylu dniach statystyk
}


def _dni(od: str | None, dzis: dt.date) -> int | None:
    if not od:
        return None
    return (dzis - dt.date.fromisoformat(od[:10])).days


def szukaj_kanalu(url: str, pobierz_kanal, data_wpisu, teraz: dt.datetime) -> str | None:
    """Szuka działającego kanału RSS/Atom w tej samej domenie (link w nagłówku strony + typowe ścieżki)."""
    u = urlparse(url)
    baza = f"{u.scheme}://{u.netloc}/"
    sciezka = u.path.rsplit("/", 1)[0] + "/" if "/" in u.path.strip("/") else "/"
    kandydaci = []
    for strona in dict.fromkeys([urljoin(baza, sciezka), baza]):
        dane, _ = pobierz_kanal(strona, timeout=15)
        if not dane:
            continue
        for tag in re.findall(r"<link[^>]+>", dane.decode("utf-8", "ignore"), re.I):
            if re.search(r"application/(rss|atom)\+xml", tag, re.I):
                h = re.search(r"href=[\"']([^\"']+)", tag)
                if h:
                    kandydaci.append(urljoin(strona, h.group(1)))
    kandydaci += [urljoin(baza, p) for p in ("feed/", "feed", "rss", "rss/", "rss.xml", "feed.xml", "atom.xml")]
    for k in dict.fromkeys(kandydaci):
        if k.rstrip("/") == url.rstrip("/") or urlparse(k).netloc != u.netloc:
            continue
        # kanał w sekcji językowej (np. /en/) musi zostać w tej sekcji, inaczej podmienimy angielski na litewski
        segmenty = [x for x in u.path.split("/") if x]
        if len(segmenty) > 1 and f"/{segmenty[0]}/" not in urlparse(k).path + "/":
            continue
        dane, _ = pobierz_kanal(k, timeout=15)
        if not dane:
            continue
        f = feedparser.parse(dane)
        if len(f.entries) < 5:
            continue
        najnowszy = max(data_wpisu(e, teraz) for e in f.entries)
        if (teraz - najnowszy).days <= 7:
            return k
    return None


def przeglad(zrodla: list[dict], jakosc: dict, stat: dict, teraz: dt.datetime, pobierz_kanal, data_wpisu,
             reguly: dict | None = None, zastosuj: bool = True) -> dict:
    r = {**REGULY, **(reguly or {})}
    dzis = teraz.date()
    dni_statystyk = [d for s in stat.values() for d in s.get("dni", {})]
    wiek_systemu = _dni(min(dni_statystyk), dzis) if dni_statystyk else 0
    zmiany, uwagi = [], []

    def zmien(z, nowy_status=None, nowy_url=None, powod=""):
        wpis = {"data": dzis.isoformat(), "id": z["id"], "nazwa": z["nazwa"], "powod": powod}
        if nowy_url:
            wpis.update({"typ": "nowy adres", "z": z["url"], "na": nowy_url})
        else:
            wpis.update({"typ": "status", "z": z["status"], "na": nowy_status})
        zmiany.append(wpis)
        if not zastosuj:
            return
        if nowy_url:
            z["url"] = nowy_url
            z["notatka"] = f"{z.get('notatka', '')} | {dzis}: auto: nowy adres kanału ({powod})".strip(" |")
        else:
            z["notatka"] = f"{z.get('notatka', '')} | {dzis}: auto: {z['status']} -> {nowy_status}, {powod}".strip(" |")
            z["status"] = nowy_status
            z["status_od"] = dzis.isoformat()

    for z in zrodla:
        if z["status"] == "zablokowane":
            continue
        s = stat.get(z["id"], {})
        j = jakosc.get(z["id"], {})

        # 1. martwy albo nieaktualny kanał
        dni_bledu = _dni(s.get("blad_od"), dzis)
        dni_ciszy = _dni(s.get("najnowszy"), dzis) if s.get("ostatnio_ok") else None
        martwy = (dni_bledu is not None and dni_bledu >= r["martwy_dni"]) or \
                 (dni_ciszy is not None and dni_ciszy >= r["nieaktualny_dni"])
        if martwy:
            od = dni_bledu if dni_bledu is not None else dni_ciszy
            opis = f"kanał nie działa od {od} dni" if dni_bledu is not None else f"najnowszy wpis sprzed {od} dni"
            nowy = szukaj_kanalu(z["url"], pobierz_kanal, data_wpisu, teraz)
            if nowy:
                zmien(z, nowy_url=nowy, powod=opis + "; znaleziony działający kanał w tej samej domenie")
            elif od >= r["martwy_blokada_dni"]:
                zmien(z, "zablokowane", powod=opis + "; brak zastępstwa")
            elif z["status"] == "aktywne":
                zmien(z, "obserwacja", powod=opis + "; szukam zastępstwa co tydzień")
            else:
                uwagi.append(f"{z['nazwa']}: {opis}, brak zastępstwa; blokada po {r['martwy_blokada_dni']} dniach.")
            continue
        if z["status"] == "monitoring":
            continue

        n = j.get("tytulow_30d", 0)
        kr = j.get("krzykliwosc") or 0.0
        traf = j.get("trafien_30d", 0)
        potw = j.get("potwierdzalnosc")

        # 2. koniec próby
        if z["status"] == "obserwacja":
            na_probie = _dni(z.get("status_od") or "2026-11-02", dzis) or 0  # start projektu jako domyślna data
            if na_probie < r["proba_dni"]:
                continue
            if n < r["min_tytulow"]:
                if zastosuj:
                    z["status_od"] = dzis.isoformat()
                uwagi.append(f"{z['nazwa']}: próba przedłużona o {r['proba_dni']} dni, za mało tytułów do oceny ({n}).")
            elif kr > r["krzyk_max"]:
                zmien(z, "zablokowane", powod=f"krzykliwe tytuły {kr*100:.0f}% (próg {r['krzyk_max']*100:.0f}%)")
            elif traf >= r["min_trafien_ocena"] and potw is not None and potw < r["potw_min"]:
                zmien(z, "zablokowane", powod=f"potwierdzalność {potw*100:.0f}% przy {traf} trafieniach (próg {r['potw_min']*100:.0f}%)")
            else:
                pw = f", potwierdzalność {potw*100:.0f}%" if potw is not None and traf >= r["min_trafien_ocena"] else ", mało alarmowych trafień"
                zmien(z, "aktywne", powod=f"próba zaliczona: krzykliwość {kr*100:.0f}%{pw}")
            continue

        # 3. aktywne, które się pogorszyło
        if z["status"] == "aktywne" and wiek_systemu >= r["karencja_dni"]:
            if n >= r["min_tytulow_degradacja"] and kr > r["krzyk_max"]:
                zmien(z, "obserwacja", powod=f"krzykliwe tytuły {kr*100:.0f}% w 30 dniach")
            elif traf >= r["min_trafien_degradacja"] and potw is not None and potw < r["potw_min"]:
                zmien(z, "obserwacja", powod=f"potwierdzalność {potw*100:.0f}% przy {traf} trafieniach")

    if wiek_systemu < r["karencja_dni"]:
        uwagi.append(f"Statystyki mają {wiek_systemu} dni; ocena aktywnych źródeł ruszy po {r['karencja_dni']} dniach.")
    return {"zmiany": zmiany, "uwagi": uwagi, "wiek_systemu": wiek_systemu}


def zapisz_log(plik, zmiany: list[dict]):
    if not zmiany:
        return
    with open(plik, "a", encoding="utf-8") as f:
        for z in zmiany:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")
