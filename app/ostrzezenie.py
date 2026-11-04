#!/usr/bin/env python3
"""Wczesne ostrzeganie: Warszawa.

Pobiera RSS z ocenionych źródeł, szuka wskaźników zagrożenia (metoda Indications & Warnings),
liczy indeks dnia, trend, alarm zbieżności i analogię do 2021/22, buduje stronę dla znajomych.

Użycie (z katalogu app/):
  python ostrzezenie.py uruchom                 # pobierz + analizuj + strona + powiadomienie
  python ostrzezenie.py zrodla lista [--status aktywne] [--min B] [--kraj PL] [--typ media]
  python ostrzezenie.py zrodla testuj URL       # sprawdź kanał przed dodaniem
  python ostrzezenie.py zrodla dodaj --id x --nazwa "X" --url URL [--typ media --kraj PL --grupa x]
  python ostrzezenie.py zrodla ocen ID --wiarygodnosc B [--notatka "..."]
  python ostrzezenie.py zrodla status ID zablokowane --powod "krzykacz, 40% tytułów sensacyjnych"
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import math
import os
import re
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import yaml

APP = Path(__file__).resolve().parent
ROOT = APP.parent
DANE = APP / "dane"
STRONA = ROOT / "strona"
PLIK_ZRODLA = APP / "zrodla.yaml"
PLIK_WSKAZNIKI = APP / "wskazniki.yaml"
PLIK_WPISY = DANE / "wpisy.jsonl"
PLIK_HISTORIA = DANE / "historia.json"
PLIK_STAT = DANE / "statystyki_zrodel.json"
PLIK_ALARM = DANE / "stan_alarmu.json"
PLIK_NAGLOWKI = DANE / "naglowki.jsonl"   # wszystkie nagłówki z 7 dni (także bez trafień): wyszukiwanie i skany na zgłoszenie
NAGLOWKI_DNI = 7
WAW = ZoneInfo("Europe/Warsaw")
from wersja import WERSJA  # noqa: E402
UA = f"Mozilla/5.0 (compatible; WczesneOstrzezenie/{WERSJA}; +https://github.com/Climbat1ze/wczesne-ostrzezenie)"
RETENCJA_DNI = 90

OCENA_MNOZNIK = {"A": 1.0, "B": 0.85, "C": 0.6, "D": 0.3, "E": 0.15, "F": 0.4}
OCENA_OPIS = {"A": "zawsze wiarygodne", "B": "zwykle wiarygodne", "C": "dość wiarygodne",
              "D": "zwykle niewiarygodne", "E": "niewiarygodne", "F": "nie da się ocenić"}
STATUSY = ["aktywne", "obserwacja", "monitoring", "zablokowane"]
KRZYK = re.compile(
    r"(!{1}|\b(szok\w*|pilne|dramat\w*|przeraż\w*|apokalip\w*|horror|koszmar\w*|"
    r"iii wojn\w*|trzeci\w* wojn\w* światow\w*|ww3|wwiii|breaking|shocking|terrifying|"
    r"bombshell|you won.t believe|panik\w*|panic)\b)", re.I)
SLOWA_STOP = set("that this with from have will were their about after into over than they them what when which "
                 "przez jest będzie oraz jako które który która tego tylko także jego może przed według rosja russia "
                 "russian rosji rosyjski ukraine ukraina ukrainy".split())


# ---------------------------------------------------------------- narzędzia

def teraz() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def wczytaj_yaml(p: Path):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def wczytaj_json(p: Path, domyslnie):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return domyslnie


def zapisz_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    tmp.replace(p)


def bez_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def tokeny(s: str) -> set[str]:
    return {t for t in re.findall(r"\w{4,}", s.lower()) if t not in SLOWA_STOP}


MIEJSCA = {
    "PL": r"\b(polsk|polsc|polan|poland|polish|warszaw|warsaw)", "LT": r"\b(litw|lithuan|wilno|wilni|vilni)",
    "LV": r"\b(łotw|latvi|ryg|riga)", "EE": r"\b(eston|tallin|narva|narw)", "BY": r"\b(białoru|belarus|mińsk|minsk|łukaszenk|lukashenk)",
    "KG": r"\b(kaliningrad|królewi|królewc|krolewiec)", "FI": r"\b(finland|finlandi|fińsk|finnish)", "BALT": r"\b(bałty|balty|baltic)",
}
MIEJSCA_RE = {k: re.compile(v, re.I) for k, v in MIEJSCA.items()}


def miejsca(s: str) -> set[str]:
    return {k for k, r in MIEJSCA_RE.items() if r.search(s)}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


# ---------------------------------------------------------------- rejestr źródeł

NAGLOWEK_ZRODEL = None


def wczytaj_zrodla() -> list[dict]:
    global NAGLOWEK_ZRODEL
    tekst = PLIK_ZRODLA.read_text(encoding="utf-8")
    NAGLOWEK_ZRODEL = tekst.split("\nzrodla:")[0]
    return yaml.safe_load(tekst)["zrodla"]


def zapisz_zrodla(zrodla: list[dict]):
    """Zapis z zachowaniem komentarzy nagłówka; jedno źródło w linii."""
    if NAGLOWEK_ZRODEL is None:
        wczytaj_zrodla()
    linie = [NAGLOWEK_ZRODEL.rstrip(), "", "zrodla:"]
    for z in zrodla:
        pary = ", ".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in z.items())
        linie.append(f"  - {{{pary}}}")
    PLIK_ZRODLA.write_text("\n".join(linie) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- słownik wskaźników

class Slownik:
    def __init__(self):
        d = wczytaj_yaml(PLIK_WSKAZNIKI)
        self.kat = d["kategorie"]
        self.wz = {k: [re.compile(p, re.I) for p in v["wzorce"]] for k, v in self.kat.items()}
        # wykluczenia: wzorce, które zdejmują kategorię mimo trafienia (np. „ulica Wojska Polskiego”); dopisuje je autoulepszanie
        self.wyk = {k: [re.compile(p, re.I) for p in v.get("wykluczenia", [])] for k, v in self.kat.items()}
        self.geo = d["geografia"]
        self.geo_wz = {k: [re.compile(p, re.I) for p in v.get("wzorce", [])] for k, v in self.geo.items()}
        self.progi = d["progi"]
        self.analogia = d["analogia_2022"]
        self.krytyczne_wz = [(k["nazwa"], [re.compile(p, re.I) for p in k["wzorce"]]) for k in d.get("sygnaly_krytyczne", [])]

    def krytyczne(self, tekst: str) -> list[str]:
        return [n for n, wz in self.krytyczne_wz if any(w.search(tekst) for w in wz)]

    def _surowe(self, tekst: str) -> list[str]:
        return [k for k, wz in self.wz.items()
                if any(w.search(tekst) for w in wz) and not any(x.search(tekst) for x in self.wyk[k])]

    def kategorie(self, tekst: str) -> list[str]:
        """Kategorie z reguł. Kategorie z flagą `tylko_przeciwnik` nie liczą działań strony własnej (app/intencja.py)."""
        kat = self._surowe(tekst)
        if any(self.kat[k].get("tylko_przeciwnik") for k in kat):
            import intencja  # noqa: E402
            if intencja.strona(tekst) == "wlasna":
                kat = [k for k in kat if not self.kat[k].get("tylko_przeciwnik")]
        return kat

    def wlasne(self, tekst: str) -> list[str]:
        """Kategorie zdjęte, bo działa strona własna (przygotowania własne: widoczne, nie podnoszą WW)."""
        kat = self._surowe(tekst)
        if not any(self.kat[k].get("tylko_przeciwnik") for k in kat):
            return []
        import intencja  # noqa: E402
        return [k for k in kat if self.kat[k].get("tylko_przeciwnik")] if intencja.strona(tekst) == "wlasna" else []

    def geografia(self, tekst: str) -> str:
        for k in ("flanka", "nato"):
            if any(w.search(tekst) for w in self.geo_wz[k]):
                return k
        return "reszta"

    def prog(self, indeks: float) -> dict:
        wynik = self.progi[0]
        for p in self.progi:
            if indeks >= p["od"]:
                wynik = p
        return wynik


# ---------------------------------------------------------------- pobieranie

def pobierz_kanal(url: str, timeout=20) -> tuple[bytes | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), "ok"
    except Exception as e:  # noqa: BLE001  — każde źródło może paść, reszta działa dalej
        return None, f"{type(e).__name__}: {str(e)[:120]}"


def data_wpisu(e, pobrano: dt.datetime) -> dt.datetime:
    for pole in ("published_parsed", "updated_parsed"):
        t = e.get(pole)
        if t:
            d = dt.datetime(*t[:6], tzinfo=dt.timezone.utc)
            return min(d, pobrano)
    return pobrano


def awaryjny_parser(dane: bytes) -> list[dict]:
    """Dla kanałów z błędnym XML (np. PAP): wyciąga <item> wyrażeniami regularnymi."""
    tekst = dane.decode("utf-8", "ignore")
    wynik = []
    for it in re.findall(r"<item\b.*?</item>", tekst, re.S | re.I):
        def pole(n):
            m = re.search(rf"<{n}[^>]*>(.*?)</{n}>", it, re.S | re.I)
            return re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S).strip() if m else ""
        d = pole("pubDate") or pole("dc:date")
        t = None
        if d:
            try:
                t = feedparser._parse_date(d)
            except Exception:  # noqa: BLE001
                t = None
        wynik.append({"title": pole("title"), "link": pole("link"), "summary": pole("description"), "published_parsed": t})
    return wynik


def parsuj(zrodlo: dict, dane: bytes, pobrano: dt.datetime, zablokowani_wydawcy: set[str]) -> list[dict]:
    feed = feedparser.parse(dane)
    entries = feed.entries or awaryjny_parser(dane)
    wpisy = []
    for e in entries[:200]:
        tytul = bez_html(e.get("title", ""))
        if not tytul:
            continue
        grupa = zrodlo["grupa"]
        wydawca = zrodlo["nazwa"]
        if grupa == "@wydawca":  # agregator: niezależność liczona po wydawcy
            wydawca = (e.get("source") or {}).get("title") or tytul.rsplit(" - ", 1)[-1]
            tytul = re.sub(r"\s+-\s+[^-]{2,60}$", "", tytul)
            grupa = "wyd:" + wydawca.lower().strip()
            if wydawca.lower().strip() in zablokowani_wydawcy:
                continue
        lead = bez_html(e.get("summary", ""))[:600]
        link = e.get("link", "")
        import linki  # noqa: E402
        wpisy.append(linki.zabezpiecz({
            "id": hashlib.sha1((link or tytul).encode()).hexdigest()[:16],
            "zrodlo": zrodlo["id"], "grupa": grupa, "wydawca": wydawca,
            "tytul": tytul, "lead": lead[:300], "link": link,
            "data": data_wpisu(e, pobrano).isoformat(timespec="minutes"),
            "_tekst": f"{tytul}. {lead}",
        }, LINKI_ODRZUCONE))
    return wpisy


def pobierz(zrodla: list[dict], slownik: Slownik) -> dict:
    pobrano = teraz()
    aktywne = [z for z in zrodla if z["status"] != "zablokowane"]
    zablokowani = {z["nazwa"].lower().split(" (")[0] for z in zrodla if z["status"] == "zablokowane"} | {"rt", "rt.com", "russia today", "sputnik", "sputnik globe", "sputniknews"}
    with ThreadPoolExecutor(max_workers=12) as ex:
        wyniki = list(ex.map(lambda z: (z, *pobierz_kanal(z["url"])), aktywne))

    stare = {}
    for w in czytaj_wpisy():
        stare[w["id"]] = w
    stat = wczytaj_json(PLIK_STAT, {})
    dzien = pobrano.astimezone(WAW).date().isoformat()
    nowe = 0
    import tlumacz  # noqa: E402
    pamiec_tl = wczytaj_json(DANE / "tlumaczenia.json", {})
    archiwum = {w["id"]: w for w in czytaj_naglowki()}
    for z, dane, blad in wyniki:
        s = stat.setdefault(z["id"], {"dni": {}, "ostatni_blad": None, "ostatnio_ok": None})
        if dane is None:
            s["ostatni_blad"] = f"{dzien}: {blad}"
            s["blad_od"] = s.get("blad_od") or dzien
            continue
        wpisy = parsuj(z, dane, pobrano, zablokowani)
        if not wpisy:
            s["ostatni_blad"] = f"{dzien}: kanał pusty lub to nie RSS"
            s["blad_od"] = s.get("blad_od") or dzien
            continue
        s["ostatnio_ok"] = pobrano.isoformat(timespec="minutes")
        s["ostatni_blad"] = None
        s["blad_od"] = None
        s["najnowszy"] = max(w["data"] for w in wpisy)[:10]
        tlumacz.przetlumacz(wpisy, z.get("jezyk", "pl"), pamiec_tl)
        for w in wpisy:
            archiwum[w["id"]] = {k: w[k] for k in ("id", "zrodlo", "grupa", "wydawca", "tytul", "link", "data") if k in w} | {
                "lead": (w.get("lead") or "")[:200], **({"oryginal": w["oryginal"], "jezyk": w["jezyk"]} if w.get("oryginal") else {})}
        # statystyka krzykliwości liczona na wszystkich tytułach, nie tylko trafieniach
        dz = s["dni"].setdefault(dzien, {"tytuly": [], "krzyk": 0})
        znane = set(dz["tytuly"])
        for w in wpisy:
            h = w["id"]
            if h not in znane:
                dz["tytuly"].append(h)
                znane.add(h)
                if KRZYK.search(w["tytul"]) or len(re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ]{4,}\b", w["tytul"])) >= 2:
                    dz["krzyk"] += 1
            kat = slownik.kategorie(w["_tekst"])
            kryt = slownik.krytyczne(w["_tekst"])
            if not (kat or kryt) or h in stare:
                continue
            w["kategorie"] = kat
            w["krytyczne"] = kryt
            w["geo"] = slownik.geografia(w["_tekst"])
            w.pop("_tekst")
            stare[h] = w
            nowe += 1
    # przycinanie
    granica = (pobrano - dt.timedelta(days=RETENCJA_DNI)).isoformat()
    wpisy = sorted((w for w in stare.values() if w["data"] >= granica), key=lambda w: w["data"])
    with open(PLIK_WPISY, "w", encoding="utf-8") as f:
        for w in wpisy:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    zapisz_naglowki(archiwum.values(), pobrano)
    for s in stat.values():
        for d in sorted(s["dni"])[:-RETENCJA_DNI]:
            del s["dni"][d]
        # zamień listy id na liczby dla dni zamkniętych (oszczędność miejsca)
        for d, v in s["dni"].items():
            if d != dzien and isinstance(v.get("tytuly"), list):
                v["n"] = len(v.pop("tytuly"))
    zapisz_json(PLIK_STAT, stat)
    zapisz_json(DANE / "tlumaczenia.json", tlumacz.przytnij(pamiec_tl))
    print(tlumacz.raport())
    ok = sum(1 for _, d, _ in wyniki if d is not None)
    print(f"Pobrano {ok}/{len(aktywne)} kanałów, nowe trafienia: {nowe}, w bazie: {len(wpisy)}")
    return {"ok": ok, "razem": len(aktywne), "nowe": nowe}


LINKI_ODRZUCONE: list[dict] = []  # odrzucone linki z bieżącego przebiegu (zapis do dane/linki_odrzucone.jsonl)


def czytaj_naglowki() -> list[dict]:
    if not PLIK_NAGLOWKI.exists():
        return []
    with open(PLIK_NAGLOWKI, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def zapisz_naglowki(wpisy, koniec: dt.datetime):
    granica = (koniec - dt.timedelta(days=NAGLOWKI_DNI)).isoformat()
    with open(PLIK_NAGLOWKI, "w", encoding="utf-8") as f:
        for w in sorted((w for w in wpisy if w.get("data", "") >= granica), key=lambda w: w["data"]):
            f.write(json.dumps(w, ensure_ascii=False) + "\n")


def czytaj_wpisy() -> list[dict]:
    """Wpisy z dysku; każdy link przechodzi kontrolę bezpieczeństwa (app/linki.py), podejrzany zastępuje strona główna redakcji."""
    if not PLIK_WPISY.exists():
        return []
    import linki  # noqa: E402
    with open(PLIK_WPISY, encoding="utf-8") as f:
        return [linki.zabezpiecz(json.loads(l), LINKI_ODRZUCONE) for l in f if l.strip()]


# ---------------------------------------------------------------- analiza

def waga_wpisu(w: dict, z: dict | None, kat: str, slownik: Slownik) -> float:
    if z is None:
        return 0.0
    status = z["status"]
    if status == "monitoring":
        if not slownik.kat[kat].get("propaganda_jako_sygnal"):
            return 0.0
        mn = 1.0  # Kreml jest wiarygodnym źródłem tego, co mówi Kreml
    elif status == "aktywne":
        import samouczenie  # noqa: E402
        mn = OCENA_MNOZNIK.get(z["wiarygodnosc"], 0.4) * samouczenie.mnoznik(z["id"])  # 0,6–1,2 z potwierdzalności
    else:
        return 0.0
    return mn * slownik.geo[w["geo"]]["mnoznik"]


def klastry(wpisy: list[dict]) -> list[list[dict]]:
    """Grupuje wpisy o tym samym wydarzeniu (podobne tytuły)."""
    gr: list[tuple[set, list]] = []
    for w in wpisy:
        t = tokeny(w["tytul"])
        for tk, lst in gr:
            if jaccard(t, tk) >= 0.45:
                lst.append(w)
                tk |= t
                break
        else:
            gr.append((set(t), [w]))
    return [lst for _, lst in gr]


def okno(wpisy, koniec: dt.datetime, godzin: int):
    pocz = (koniec - dt.timedelta(hours=godzin)).isoformat()
    kon = koniec.isoformat()
    return [w for w in wpisy if pocz <= w["data"] <= kon]


def analiza_dnia(wpisy, zrodla_idx, slownik: Slownik, koniec: dt.datetime) -> dict:
    dzien = okno(wpisy, koniec, 24)
    K = 4.0
    natezenie, sila = {}, {}
    for kat in slownik.kat:
        ww = [w for w in dzien if kat in w["kategorie"]]
        s = 0.0
        for kl in klastry(ww):
            s += max(waga_wpisu(w, zrodla_idx.get(w["zrodlo"]), kat, slownik) for w in kl)
        sila[kat] = round(s, 2)
        natezenie[kat] = round(1 - math.exp(-s / K), 3)
    poz = {k: v for k, v in slownik.kat.items() if v["waga"] > 0}
    suma_wag = sum(v["waga"] for v in poz.values())
    indeks = 100 * sum(v["waga"] * natezenie[k] for k, v in poz.items()) / suma_wag
    indeks *= (1 - 0.3 * natezenie.get("deeskalacja", 0))
    return {"indeks": round(indeks, 1), "natezenie": natezenie, "sila": sila,
            "wpisow_24h": len(dzien)}


def zbieznosc(wpisy, zrodla_idx, slownik: Slownik, koniec: dt.datetime) -> dict:
    """Alarm zbieżności: ile niezależnych grup źródeł (A–C) mówi o tej samej kategorii wobec flanki w 72 h."""
    ww = okno(wpisy, koniec, 72)
    kat_grupy = {}
    for kat, v in slownik.kat.items():
        if not v.get("wysoka"):
            continue
        grupy = defaultdict(list)
        for w in ww:
            if kat not in w["kategorie"] or w["geo"] != "flanka":
                continue
            z = zrodla_idx.get(w["zrodlo"])
            if not z:
                continue
            if z["status"] == "aktywne" and z["wiarygodnosc"] in "ABC":
                grupy[w["grupa"]].append(w)
            elif z["status"] == "monitoring" and v.get("propaganda_jako_sygnal"):
                grupy[w["grupa"]].append(w)
        kat_grupy[kat] = grupy
    zbiezne = [k for k, g in kat_grupy.items() if len(g) >= 3]
    twarde = {"ewakuacja", "ostrzezenia_sojusznikow", "przestrzen_transport", "gotowosc"}
    if len(zbiezne) >= 3 and twarde & set(zbiezne):
        poziom = 3
    elif len(zbiezne) >= 2:
        poziom = 2
    elif zbiezne:
        poziom = 1
    else:
        poziom = 0
    return {
        "poziom": poziom,
        "nazwa": ["Brak spiętrzenia", "Uwaga", "Ostrzeżenie", "Alarm"][poziom],
        "kategorie": {k: {"grupy": len(g), "przyklady": [
            {"tytul": l[0]["tytul"], "link": l[0]["link"], "wydawca": l[0]["wydawca"]}
            for l in list(g.values())[:4]]} for k, g in kat_grupy.items()},
        "zbiezne": zbiezne,
    }


def analogia(wpisy, zrodla_idx, slownik: Slownik, koniec: dt.datetime) -> list[dict]:
    ww = okno(wpisy, koniec, 24 * 30)
    wynik = []
    for a in slownik.analogia:
        kat = a["kategoria"]
        grupy = {}
        for w in ww:
            if kat in w["kategorie"] and w["geo"] == "flanka" and waga_wpisu(w, zrodla_idx.get(w["zrodlo"]), kat, slownik) >= 0.5:
                grupy.setdefault(w["grupa"], w)
        przyk = sorted(grupy.values(), key=lambda w: w["data"], reverse=True)[:2]
        wynik.append({**a, "trafienie": len(grupy) >= 2, "grup": len(grupy),
                      "przyklady": [{"tytul": p["tytul"], "link": p["link"], "wydawca": p["wydawca"]} for p in przyk]})
    return wynik


def najwazniejsze(wpisy, zrodla_idx, slownik: Slownik, koniec: dt.datetime, n=12) -> list[dict]:
    dzien = [w for w in okno(wpisy, koniec, 24) if w["geo"] != "reszta"]
    wynik = []
    for kl in klastry(dzien):
        kats = sorted({k for w in kl for k in w["kategorie"]})
        poz = [k for k in kats if slownik.kat[k]["waga"] > 0]
        if not poz:
            continue
        wagi = [max(waga_wpisu(w, zrodla_idx.get(w["zrodlo"]), k, slownik) for k in poz) for w in kl]
        if max(wagi) == 0:
            continue
        grupy = {w["grupa"] for w in kl}
        ocena = sum(slownik.kat[k]["waga"] for k in poz) * max(wagi) * (1 + 0.5 * (len(grupy) - 1))
        glowny = kl[wagi.index(max(wagi))]
        wynik.append({"tytul": glowny["tytul"], "link": glowny["link"], "lead": glowny.get("lead", ""),
                      "jezyk": glowny.get("jezyk"), "oryginal": glowny.get("oryginal"),
                      "data": glowny["data"], "kategorie": poz, "ocena": round(ocena, 2),
                      "zrodla": sorted({(w["wydawca"], w["link"]) for w in kl})[:6],
                      "grup": len(grupy)})
    return sorted(wynik, key=lambda x: -x["ocena"])[:n]


def jakosc_zrodel(wpisy, zrodla, slownik: Slownik) -> dict:
    """Krzykliwość tytułów i potwierdzalność trafień przez inne grupy z oceną A/B (30 dni)."""
    stat = wczytaj_json(PLIK_STAT, {})
    idx = {z["id"]: z for z in zrodla}
    granica = (teraz() - dt.timedelta(days=30)).isoformat()
    ww = [w for w in wpisy if w["data"] >= granica]
    po_kat = defaultdict(list)
    for w in ww:
        for k in w["kategorie"]:
            po_kat[k].append(w)
    wynik = {}
    for z in zrodla:
        s = stat.get(z["id"], {})
        dni = s.get("dni", {})
        n = sum(v.get("n", len(v.get("tytuly", []))) for v in dni.values())
        krzyk = sum(v.get("krzyk", 0) for v in dni.values())
        moje = [w for w in ww if w["zrodlo"] == z["id"] and w["geo"] != "reszta"
                and any(slownik.kat[k].get("wysoka") for k in w["kategorie"])]
        potw = 0
        for w in moje:
            t = tokeny(w["tytul"])
            m = miejsca(w["tytul"] + " " + w.get("lead", ""))
            d0 = dt.datetime.fromisoformat(w["data"])
            ok = False
            for k in w["kategorie"]:
                for inny in po_kat[k]:
                    zi = idx.get(inny["zrodlo"])
                    if inny["grupa"] == w["grupa"] or not zi or zi["wiarygodnosc"] not in "AB" or zi["status"] != "aktywne":
                        continue
                    if abs((dt.datetime.fromisoformat(inny["data"]) - d0).total_seconds()) <= 48 * 3600 and (
                            jaccard(t, tokeny(inny["tytul"])) >= 0.12
                            or m & miejsca(inny["tytul"] + " " + inny.get("lead", ""))):
                        ok = True
                        break
                if ok:
                    break
            potw += ok
        flagi = []
        if n >= 20 and krzyk / n > 0.15:
            flagi.append("krzykliwe tytuły")
        if len(moje) >= 5 and potw / len(moje) < 0.3:
            flagi.append("słabo potwierdzane")
        if s.get("ostatni_blad"):
            flagi.append("kanał nie działa")
        wynik[z["id"]] = {
            "tytulow_30d": n, "krzykliwosc": round(krzyk / n, 3) if n else None,
            "trafien_30d": len(moje), "potwierdzalnosc": round(potw / len(moje), 3) if moje else None,
            "ostatnio_ok": s.get("ostatnio_ok"), "ostatni_blad": s.get("ostatni_blad"), "flagi": flagi,
        }
    return wynik


def czytaj_wpisy_analizy(zrodla, slownik: Slownik) -> list[dict]:
    # Klasyfikacja od nowa przy każdym przebiegu: poprawki słownika działają wstecz na całe 90 dni.
    # Potem warstwa intencji: zapisany werdykt modelu może zdjąć kategorię (app/intencja.py), reguły strony działają zawsze.
    import intencja  # noqa: E402
    wpisy = []
    for w in czytaj_wpisy():
        tekst = f"{w['tytul']}. {w.get('lead', '')}"
        w["kategorie"] = slownik.kategorie(tekst)
        w["krytyczne"] = slownik.krytyczne(tekst)
        w["wlasne"] = slownik.wlasne(tekst)
        w["geo"] = slownik.geografia(tekst)
        intencja.zastosuj(w, slownik.kat)
        if w["kategorie"] or w["krytyczne"] or w["wlasne"] or (w.get("intencja") or {}).get("zdjete"):
            wpisy.append(w)
    return wpisy


def przygotowania_wlasne(wpisy, koniec: dt.datetime, n: int = 8) -> list[dict]:
    """Wpisy, w których działa strona własna lub sojusznicza (reguły albo model). Widoczne, nie podnoszą WW."""
    wynik = []
    nazwy = {k: v["nazwa"].lower() for k, v in Slownik().kat.items()}
    for kl in klastry([w for w in okno(wpisy, koniec, 72) if w.get("wlasne") or (w.get("intencja") or {}).get("zdjete")]):
        g = kl[0]
        zdjete = sorted({k for w in kl for k in (w.get("wlasne") or []) + ((w.get("intencja") or {}).get("zdjete") or [])})
        wynik.append({"tytul": g["tytul"], "link": g["link"], "wydawca": g["wydawca"], "data": g["data"], "zdjete": zdjete, "zdjete_nazwy": [nazwy.get(k, k) for k in zdjete],
                      "powod": ((g.get("intencja") or {}).get("powod") or "reguła: działa strona własna lub sojusznicza"),
                      "grup": len({w["grupa"] for w in kl})})
    return sorted(wynik, key=lambda x: x["data"], reverse=True)[:n]


def analizuj(zrodla, slownik: Slownik, rekonstrukcja_dni=14) -> dict:
    wpisy = czytaj_wpisy_analizy(zrodla, slownik)
    idx = {z["id"]: z for z in zrodla}
    teraz_ = teraz()
    import intencja  # noqa: E402
    if intencja.weryfikuj(wpisy, idx, slownik.kat, teraz_):
        wpisy = czytaj_wpisy_analizy(zrodla, slownik)  # werdykty modelu nałożone na wpisy
    historia = wczytaj_json(PLIK_HISTORIA, {"dni": {}})
    # rekonstrukcja dni, których nie ma w historii (z archiwum kanałów RSS, niepełna)
    for i in range(rekonstrukcja_dni, 0, -1):
        d = (teraz_.astimezone(WAW) - dt.timedelta(days=i)).date()
        if d.isoformat() in historia["dni"]:
            continue
        koniec = dt.datetime.combine(d, dt.time(23, 59), WAW).astimezone(dt.timezone.utc)
        a = analiza_dnia(wpisy, idx, slownik, koniec)
        if a["wpisow_24h"] == 0:
            continue
        z = zbieznosc(wpisy, idx, slownik, koniec)
        historia["dni"][d.isoformat()] = {"indeks": a["indeks"], "natezenie": a["natezenie"],
                                          "alarm": z["poziom"], "rekonstrukcja": True}
    a = analiza_dnia(wpisy, idx, slownik, teraz_)
    z = zbieznosc(wpisy, idx, slownik, teraz_)
    an = analogia(wpisy, idx, slownik, teraz_)
    dzis = teraz_.astimezone(WAW).date().isoformat()
    historia["dni"][dzis] = {"indeks": a["indeks"], "natezenie": a["natezenie"], "alarm": z["poziom"],
                             "rekonstrukcja": False, "aktualizacja": teraz_.isoformat(timespec="minutes")}
    for d in sorted(historia["dni"])[:-400]:
        del historia["dni"][d]
    zapisz_json(PLIK_HISTORIA, historia)

    dni = sorted(historia["dni"].items())
    poprzednie = [v["indeks"] for _, v in dni[:-1]]
    trend = {
        "wczoraj": poprzednie[-1] if poprzednie else None,
        "sr_7": round(sum(poprzednie[-7:]) / len(poprzednie[-7:]), 1) if poprzednie else None,
        "sr_30": round(sum(poprzednie[-30:]) / len(poprzednie[-30:]), 1) if poprzednie else None,
        "dni_historii": len(poprzednie),
    }
    # skoki kategorii względem 30 dni
    skoki = []
    for k in slownik.kat:
        if slownik.kat[k]["waga"] <= 0:
            continue
        prev = [v["natezenie"].get(k, 0) for _, v in dni[:-1]][-30:]
        if len(prev) >= 5:
            sr = sum(prev) / len(prev)
            if a["natezenie"][k] >= 0.5 and a["natezenie"][k] >= 2 * sr + 0.15:
                skoki.append(k)
    wynik = {
        "wygenerowano": teraz_.isoformat(timespec="minutes"),
        "dzien": dzis, **a, "prog": slownik.prog(a["indeks"]), "trend": trend,
        "zbieznosc": z, "analogia": an, "skoki": skoki, "trend_alarm": trend_alarm(dni),
        "najwazniejsze": najwazniejsze(wpisy, idx, slownik, teraz_),
        "jakosc": jakosc_zrodel(wpisy, zrodla, slownik),
        "wlasne": przygotowania_wlasne(wpisy, teraz_), "intencja": intencja.statystyki(),
        "historia": [{"dzien": d, "indeks": v["indeks"], "alarm": v["alarm"], "rek": v.get("rekonstrukcja", False)} for d, v in dni],
    }
    wynik["skrot"] = skrot(wynik, slownik)
    zapisz_json(DANE / "ostatnia_analiza.json", {k: v for k, v in wynik.items() if k != "jakosc"})
    return wynik


def strzalka(teraz_v, ref):
    if ref is None:
        return "brak porównania"
    d = teraz_v - ref
    if abs(d) < 3:
        return f"bez zmian ({d:+.0f})"
    return f"{'wzrost' if d > 0 else 'spadek'} {d:+.0f}"


def skrot(w: dict, slownik: Slownik) -> list[str]:
    """Kilka zdań skrótu dnia, budowanych regułami (bez modelu językowego, w pełni sprawdzalne)."""
    t = w["trend"]
    zd = [f"Poziom: {w['prog']['nazwa'].lower()}, współczynnik wpierdolu {w['indeks']:.0f}/100. "
          f"Wobec tygodnia: {strzalka(w['indeks'], t['sr_7'])}; wobec miesiąca: {strzalka(w['indeks'], t['sr_30'])}."]
    top = sorted(((k, v) for k, v in w["natezenie"].items() if slownik.kat[k]["waga"] > 0 and v >= 0.25),
                 key=lambda kv: -kv[1] * slownik.kat[kv[0]]["waga"])[:3]
    if top:
        zd.append("Najsilniejsze sygnały: " + "; ".join(
            f"{slownik.kat[k]['nazwa'].lower()} ({v*100:.0f}% skali)" for k, v in top) + ".")
    else:
        zd.append("Żadna kategoria wskaźników nie przekroczyła 25% skali w ostatnich 24 godzinach.")
    z = w["zbieznosc"]
    if z["poziom"]:
        zd.append(f"Spiętrzenie zbieżnych komunikatów: {z['nazwa'].lower()}. Co najmniej 3 niezależne redakcje w 72 h w kategoriach: "
                  + ", ".join(slownik.kat[k]["nazwa"].lower() for k in z["zbiezne"]) + ".")
    else:
        zd.append("Brak spiętrzenia: żadna kategoria nie ma 3 niezależnych potwierdzeń wobec Polski i Bałtów w 72 h.")
    dees = w["natezenie"].get("deeskalacja", 0)
    if dees >= 0.25:
        zd.append(f"Sygnały deeskalacji obecne ({dees*100:.0f}% skali), obniżają indeks.")
    tr = sum(a["trafienie"] for a in w["analogia"])
    zd.append(f"Analogia do okresu przed 24.02.2022: {tr} z {len(w['analogia'])} kamieni milowych ma dziś odpowiednik wobec flanki.")
    ta = w.get("trend_alarm") or {}
    if ta.get("stan") == "alarm":
        zd.append(f"Trend wzrostowy: {ta['opis']}")
    elif ta.get("stan") == "zbieram":
        zd.append(f"Alarm trendu: {ta['opis']}")
    if w["skoki"]:
        zd.append("Nagły skok wobec średniej 30 dni: " + ", ".join(slownik.kat[k]["nazwa"].lower() for k in w["skoki"]) + ".")
    return zd


# ---------------------------------------------------------------- sygnały krytyczne i harmonogram

KARENCJA_DNI = 30
START_REJESTRU = "2026-11-02"  # źródła z pierwotnego rejestru (sprawdzone ręcznie przy starcie) są bez karencji


def w_karencji(z: dict, dzis: dt.date | None = None) -> bool:
    """Źródło dodane do rejestru po starcie projektu nie liczy się do sygnału krytycznego przez 30 dni."""
    dodano = z.get("dodano") or START_REJESTRU
    if dodano <= START_REJESTRU:
        return False
    dzis = dzis or teraz().astimezone(WAW).date()
    return (dzis - dt.date.fromisoformat(dodano[:10])).days < KARENCJA_DNI


def sygnaly_krytyczne(wpisy, zrodla_idx, koniec: dt.datetime) -> list[dict]:
    """Sygnał krytyczny: konkretne zdarzenie wobec flanki, opisane przez min. 2 niezależne redakcje A/B w 24 h.
    Źródła w karencji (dodane w ostatnich 30 dniach) się nie liczą."""
    po_nazwie = defaultdict(dict)
    dzis = koniec.astimezone(WAW).date()
    for w in okno(wpisy, koniec, 24):
        z = zrodla_idx.get(w["zrodlo"])
        if not z or z["status"] != "aktywne" or z["wiarygodnosc"] not in "AB" or w["geo"] != "flanka":
            continue
        if w_karencji(z, dzis):
            continue
        for n in w.get("krytyczne", []):
            po_nazwie[n].setdefault(w["grupa"], w)
    return [{"nazwa": n, "grup": len(g), "przyklady": [
        {"tytul": x["tytul"], "link": x["link"], "wydawca": x["wydawca"], "data": x["data"]} for x in list(g.values())[:5]]}
        for n, g in po_nazwie.items() if len(g) >= 2]


TREND = {"baza_dni": 30, "min_baza": 14, "okno_dni": 14, "k_sigma": 0.5, "h_sigma": 4.0, "min_sigma": 3.0,
         "min_nadwyzka_7d": 8.0}


def trend_alarm(dni: list) -> dict:
    """Powolne narastanie (CUSUM, E. S. Page 1954): suma dziennych nadwyżek indeksu ponad normę z poprzednich 30 dni.

    Norma = średnia z dni od 8. do 37. wstecz (ostatni tydzień nie zawyża własnej normy). Każdy dzień dokłada
    (indeks - norma - 0,5 sigma), suma nie spada poniżej zera. Alarm, gdy suma z 14 dni przekroczy 4 sigma
    i średnia z 7 dni jest co najmniej 8 pkt nad normą. Dni odtworzone z archiwum RSS pomijane.
    """
    r = TREND
    prawdziwe = [(d, v["indeks"]) for d, v in dni if not v.get("rekonstrukcja")]
    baza = [x for _, x in prawdziwe[:-7]][-r["baza_dni"]:]
    if len(baza) < r["min_baza"]:
        return {"stan": "zbieram", "opis": f"zbieram historię, {len(prawdziwe)} z {r['min_baza'] + 7} potrzebnych dni.",
                "dni": len(prawdziwe)}
    norma = sum(baza) / len(baza)
    sigma = max(r["min_sigma"], (sum((x - norma) ** 2 for x in baza) / len(baza)) ** 0.5)
    suma = 0.0
    for _, x in prawdziwe[-r["okno_dni"]:]:
        suma = max(0.0, suma + (x - norma - r["k_sigma"] * sigma))
    ost7 = [x for _, x in prawdziwe[-7:]]
    nadwyzka = sum(ost7) / len(ost7) - norma
    alarm = suma >= r["h_sigma"] * sigma and nadwyzka >= r["min_nadwyzka_7d"]
    opis = (f"średnia z 7 dni {nadwyzka:+.0f} pkt wobec normy {norma:.0f} z poprzednich {len(baza)} dni; "
            f"suma nadwyżek {suma:.0f} przy progu {r['h_sigma'] * sigma:.0f}.")
    return {"stan": "alarm" if alarm else "norma", "opis": opis, "norma": round(norma, 1), "sigma": round(sigma, 1),
            "suma": round(suma, 1), "prog": round(r["h_sigma"] * sigma, 1), "nadwyzka_7d": round(nadwyzka, 1)}


def powiadom_trend(w: dict) -> bool:
    """Mail, gdy alarm trendu się włącza; przy trwającym alarmie przypomnienie najwyżej raz na 7 dni."""
    ta = w.get("trend_alarm") or {}
    stan = wczytaj_json(DANE / "stan_trendu.json", {"stan": "norma", "ostatni_mail": None})
    wyslac = False
    if ta.get("stan") == "alarm":
        ost = stan.get("ostatni_mail")
        wyslac = stan.get("stan") != "alarm" or not ost or \
            (teraz() - dt.datetime.fromisoformat(ost)).total_seconds() >= 7 * 86400
    if wyslac:
        import koszty, poczta  # noqa: E402
        koszty.wyslij_alarm(*poczta.zbuduj_trend(w), rodzaj="trend")
        stan["ostatni_mail"] = teraz().isoformat(timespec="minutes")
    stan["stan"] = ta.get("stan", "norma")
    zapisz_json(DANE / "stan_trendu.json", stan)
    return wyslac


def powiadom_krytyczne(w: dict) -> list[dict]:
    stan = wczytaj_json(DANE / "krytyczne_wyslane.json", {})
    nowe = []
    for k in w["krytyczne"]:
        ost = stan.get(k["nazwa"])
        if ost and (teraz() - dt.datetime.fromisoformat(ost)).total_seconds() < 72 * 3600:
            continue
        nowe.append(k)
        stan[k["nazwa"]] = teraz().isoformat(timespec="minutes")
    if nowe:
        import koszty, poczta  # noqa: E402
        koszty.wyslij_alarm(*poczta.zbuduj_krytyczny(nowe, w), rodzaj="krytyczny")
        zapisz_json(DANE / "krytyczne_wyslane.json", stan)
    return nowe


def harmonogram(teraz_utc: dt.datetime) -> dict:
    """Decyduje, czy w tym przebiegu wysłać skrót (godziny z STATUS_GODZINY, czas Warszawy) i czy zrobić przegląd źródeł (poniedziałek rano)."""
    stan = wczytaj_json(DANE / "harmonogram.json", {"skroty": [], "utrzymanie": None})
    t = teraz_utc.astimezone(WAW)
    try:
        godziny = sorted({int(x) % 24 for x in os.environ.get("STATUS_GODZINY", "6").replace(" ", "").split(",") if x})
    except ValueError:
        godziny = [6]
    try:
        dni = {int(x) for x in os.environ.get("STATUS_DNI", "1,2,3,4,5,6,7").replace(" ", "").split(",") if x}
    except ValueError:
        dni = set(range(1, 8))
    slot = None
    for h in (godziny if t.isoweekday() in dni else []):
        kandydat = f"{t.date().isoformat()}T{h:02d}"
        if 0 <= t.hour - h <= 1 and kandydat not in stan["skroty"]:  # okno 2 h: cron w GitHub bywa opóźniony
            slot = kandydat
            break
    tydzien = f"{t.isocalendar().year}-W{t.isocalendar().week:02d}"
    utrz = t.weekday() == 0 and t.hour >= (godziny[0] if godziny else 6) and stan.get("utrzymanie") != tydzien
    return {"stan": stan, "slot": slot, "tydzien": tydzien, "utrzymanie": utrz}


def zapisz_harmonogram(h: dict, skrot_wyslany: bool, utrzymanie_zrobione: bool):
    stan = h["stan"]
    if skrot_wyslany and h["slot"]:
        stan["skroty"] = (stan["skroty"] + [h["slot"]])[-30:]
    if utrzymanie_zrobione:
        stan["utrzymanie"] = h["tydzien"]
    zapisz_json(DANE / "harmonogram.json", stan)


# ---------------------------------------------------------------- powiadomienia

def powiadom(w: dict, slownik: "Slownik"):
    stan = wczytaj_json(PLIK_ALARM, {"poziom": 0, "dzien": None})
    poziom = w["zbieznosc"]["poziom"]
    kolor_prog = w["prog"]["kolor"]
    wzrost = poziom > stan.get("poziom", 0)
    zapisz_json(PLIK_ALARM, {"poziom": poziom, "dzien": w["dzien"], "prog": kolor_prog})
    if not (wzrost and poziom >= 2):
        print(f"Powiadomienie: nie (poziom alarmu {poziom}, poprzednio {stan.get('poziom', 0)})")
        return
    import koszty, poczta  # noqa: E402
    koszty.wyslij_alarm(*poczta.zbuduj(w, slownik, "alarm"), rodzaj="spietrzenie")


# ---------------------------------------------------------------- CLI: źródła

def cmd_zrodla(args):
    zrodla = wczytaj_zrodla()
    slownik = Slownik()
    if args.akcja == "przeglad":
        print("Podgląd (bez zmian w rejestrze). Reguły: app/utrzymanie.py")
        utrzymaj_zrodla(zrodla, jakosc_zrodel(czytaj_wpisy(), zrodla, slownik), zastosuj=False)
    elif args.akcja == "lista":
        jak = jakosc_zrodel(czytaj_wpisy(), zrodla, slownik)
        rang = "ABCDEF"
        for z in zrodla:
            if args.status and z["status"] != args.status:
                continue
            if args.min and rang.index(z["wiarygodnosc"]) > rang.index(args.min):
                continue
            if args.kraj and z["kraj"] != args.kraj:
                continue
            if args.typ and z["typ"] != args.typ:
                continue
            j = jak.get(z["id"], {})
            kr = f"{j['krzykliwosc']*100:.0f}%" if j.get("krzykliwosc") is not None else "–"
            po = f"{j['potwierdzalnosc']*100:.0f}%" if j.get("potwierdzalnosc") is not None else "–"
            print(f"{z['id']:<20} {z['wiarygodnosc']} {z['status']:<11} {z['kraj']:<3} {z['typ']:<15} "
                  f"krzyk {kr:>4}  potw {po:>4}  {', '.join(j.get('flagi', []))}")
    elif args.akcja == "testuj":
        dane, blad = pobierz_kanal(args.cel)
        if dane is None:
            print("Nie działa:", blad)
            return 1
        z = {"id": "test", "nazwa": "test", "grupa": "test"}
        wpisy = parsuj(z, dane, teraz(), set())
        if not wpisy:
            print("Odpowiedź przyszła, ale to nie jest kanał RSS/Atom albo jest pusty.")
            return 1
        krzyk = sum(1 for w in wpisy if KRZYK.search(w["tytul"]))
        traf = [(w, slownik.kategorie(w["_tekst"]), slownik.geografia(w["_tekst"])) for w in wpisy]
        daty = sorted(w["data"] for w in wpisy)
        print(f"Wpisów: {len(wpisy)}, od {daty[0][:10]} do {daty[-1][:10]}")
        print(f"Krzykliwe tytuły: {krzyk}/{len(wpisy)} ({krzyk/len(wpisy)*100:.0f}%)  [próg ostrzeżenia: 15%]")
        print(f"Trafienia wskaźników: {sum(1 for _, k, _ in traf if k)}, w tym o flance: {sum(1 for _, k, g in traf if k and g == 'flanka')}")
        for w, k, g in traf[:8]:
            print(f"  - {w['tytul'][:100]}  {('[' + ','.join(k) + ']') if k else ''}")
    elif args.akcja == "dodaj":
        if any(z["id"] == args.id for z in zrodla):
            print("Takie id już jest.")
            return 1
        if any(z["url"] == args.url for z in zrodla):
            print("Ten adres już jest w rejestrze:", next(z["id"] for z in zrodla if z["url"] == args.url))
            return 1
        dane, blad = pobierz_kanal(args.url)
        if dane is None or not feedparser.parse(dane).entries:
            print("Kanał nie działa albo nie jest RSS:", blad)
            return 1
        zrodla.append({"id": args.id, "nazwa": args.nazwa, "url": args.url, "typ": args.typ, "kraj": args.kraj,
                       "perspektywa": args.perspektywa, "grupa": args.grupa or args.id, "jezyk": args.jezyk,
                       "wiarygodnosc": args.wiarygodnosc, "status": "obserwacja", "status_od": dt.date.today().isoformat(), "dodano": dt.date.today().isoformat(),
                       "notatka": f"Dodane {dt.date.today()}; okres próbny 30 dni. {args.notatka or ''}".strip()})
        zapisz_zrodla(zrodla)
        print(f"Dodano {args.id} w statusie „obserwacja”. Po 30 dniach sprawdź krzykliwość i potwierdzalność, potem: zrodla status {args.id} aktywne")
    elif args.akcja == "ocen":
        z = next((z for z in zrodla if z["id"] == args.cel), None)
        if not z:
            print("Nie ma źródła", args.cel)
            return 1
        z["wiarygodnosc"] = args.wiarygodnosc
        if args.notatka:
            z["notatka"] = f"{z['notatka']} | {dt.date.today()}: ocena {args.wiarygodnosc}, {args.notatka}".strip(" |")
        zapisz_zrodla(zrodla)
        print(f"{z['id']}: wiarygodność {args.wiarygodnosc} ({OCENA_OPIS[args.wiarygodnosc]})")
    elif args.akcja == "status":
        z = next((z for z in zrodla if z["id"] == args.cel), None)
        if not z or args.nowy not in STATUSY:
            print("Podaj istniejące id i status z listy:", ", ".join(STATUSY))
            return 1
        z["status"] = args.nowy
        z["status_od"] = dt.date.today().isoformat()
        z["notatka"] = f"{z['notatka']} | {dt.date.today()}: status {args.nowy}{', ' + args.powod if args.powod else ''}".strip(" |")
        zapisz_zrodla(zrodla)
        print(f"{z['id']}: status {args.nowy}")
    return 0


# ---------------------------------------------------------------- main

def cmd_uruchom(args):
    import time  # noqa: E402
    start = time.monotonic()
    zrodla = wczytaj_zrodla()
    slownik = Slownik()
    DANE.mkdir(exist_ok=True)
    stan_pobrania = None
    if not args.bez_pobierania:
        stan_pobrania = pobierz(zrodla, slownik)
    w = analizuj(zrodla, slownik)
    w["pobranie"] = stan_pobrania
    w["utrzymanie"] = None
    h = harmonogram(teraz()) if args.harmonogram else None
    if h:
        args.mail_skrot = args.mail_skrot or bool(h["slot"])
        args.utrzymanie_zrodel = args.utrzymanie_zrodel or h["utrzymanie"]
    if args.utrzymanie_zrodel:
        w["utrzymanie"] = utrzymaj_zrodla(zrodla, w["jakosc"], zastosuj=True)
        w["raport_admin"] = True
        if args.znacznik_main:
            Path(args.znacznik_main).write_text("1")
    w["krytyczne"] = sygnaly_krytyczne(czytaj_wpisy_analizy(zrodla, slownik), {z["id"]: z for z in zrodla}, teraz())
    import strona  # noqa: E402
    strona.zbuduj(w, zrodla, slownik)
    zapisz_skrot_md(w, slownik)
    kontrola_zdrowia(stan_pobrania, args.bez_powiadomien)
    if w.get("raport_admin"):
        import jakosc, samouczenie  # noqa: E402
        w["ocena"] = jakosc.ocena_trafnosci(czytaj_wpisy_analizy(zrodla, slownik), slownik.kat)
        _, w["zmiany_wiarygodnosci"] = samouczenie.zapisz_mnozniki(w["jakosc"])
        w["oceny"] = samouczenie.wczytaj_oceny({x["id"]: x for x in czytaj_wpisy()}, slownik)
        print(f"Oceny właściciela: nowe przypadki wpisów {w['oceny']['nowe_wpisy']}, alarmów {w['oceny']['nowe_alarmy']}"
              + (f", błąd: {w['oceny']['blad']}" if w["oceny"]["blad"] else ""))
        if (w["oceny"]["nowe_wpisy"] or w["oceny"]["nowe_alarmy"]) and args.znacznik_main:
            Path(args.znacznik_main).write_text("1")
    if not args.bez_powiadomien:
        powiadom(w, slownik)
        if powiadom_trend(w):
            print("ALARM TRENDU:", w["trend_alarm"]["opis"])
        for k in powiadom_krytyczne(w):
            print(f"SYGNAŁ KRYTYCZNY: {k['nazwa']} ({k['grup']} redakcje)")
        import koszty  # noqa: E402
        if koszty.oproznij_kolejke(godzina_raportu(teraz())):
            print("Wysłano zbiorczo wstrzymane alarmy")
    if args.status_md:
        Path(args.status_md).write_text(status_md(w, slownik), encoding="utf-8")
        print("Status:", args.status_md)
    if args.mail_skrot or args.podglad_maila:
        import poczta  # noqa: E402
        if os.environ.get("STATUS_FORMA", "dzien") == "tydzien":
            temat, tekst, html_ = poczta.zbuduj_tydzien(w, slownik)
        else:
            temat, tekst, html_ = poczta.zbuduj(w, slownik, "skrot")
        if args.podglad_maila:
            Path(args.podglad_maila).write_text(html_, encoding="utf-8")
            print("Podgląd maila:", args.podglad_maila, "|", temat)
        if args.mail_skrot and poczta.wyslij(temat, tekst, html_):
            import koszty  # noqa: E402
            koszty.zapisz_mail("raport", temat)
    if h:
        zapisz_harmonogram(h, bool(args.mail_skrot), bool(args.utrzymanie_zrodel))
    import koszty  # noqa: E402
    pob = stan_pobrania or {}
    koszty.zapisz_przebieg(time.monotonic() - start, pob.get("ok"), pob.get("razem"))
    if w.get("raport_admin") and not args.bez_powiadomien:
        wyslij_raport_admin(w)
    import linki  # noqa: E402
    n_odrz = linki.zapisz_odrzucone(DANE, LINKI_ODRZUCONE)
    if LINKI_ODRZUCONE:
        print(f"Linki: odrzucone {len({x['id'] for x in LINKI_ODRZUCONE})} (nowe {n_odrz}), zastąpione stroną główną redakcji")
    print("\n".join(w["skrot"]))
    return 0


def godzina_raportu(t: dt.datetime) -> bool:
    try:
        godziny = {int(x) % 24 for x in os.environ.get("STATUS_GODZINY", "7").replace(" ", "").split(",") if x}
    except ValueError:
        godziny = {7}
    return t.astimezone(WAW).hour in godziny


def sekcje_admin(w: dict) -> list[tuple[str, list[str]]]:
    """Dodatkowe sekcje raportu administracyjnego."""
    import jakosc  # noqa: E402
    import samouczenie  # noqa: E402
    import zgloszenia  # noqa: E402
    oc = w.get("oceny") or {}
    it = w.get("intencja") or {}
    linie_int = [f"Model ocenił w 7 dniach {it.get('ocenione', 0)} wpisów: " + (", ".join(f"{k} {v}" for k, v in (it.get("po_stronie") or {}).items()) or "brak") + "."]
    linie_int += [f"Strona własna lub sojusznicza: „{t}”" for t in it.get("przyklady_wlasne", [])[:3]]
    from wersja import WERSJA  # noqa: E402
    return [("WERSJA", [f"Aplikacja w wersji {WERSJA}. Historia zmian: CHANGELOG.md, zgłoszenia zmian: docs/change_requests.md."]),
            ("ZGŁOSZENIA I ANALIZA WSTECZNA", zgloszenia.linie_podsumowania()),
            ("KONTROLA INTENCJI", linie_int),
            ("ZDROWIE PRZEBIEGÓW", jakosc.linie_zdrowia()),
            ("JAKOŚĆ KLASYFIKACJI", jakosc.linie_jakosci(w.get("ocena"))),
            ("WIARYGODNOŚĆ ŹRÓDEŁ Z DANYCH", (w.get("zmiany_wiarygodnosci") or ["Bez zmian mnożników (0,6–1,2 do oceny A–F)."])
             + [f"Mnożnik liczy się od {samouczenie.MIN_TRAFIEN} alarmowych trafień źródła w 30 dniach."]),
            ("OCEŃ ALARMY I POMYŁKI", samouczenie.linie_ocen((w.get("ocena") or {}).get("bledne", []))
             + [f"Wczytane od ostatniego razu: {oc.get('nowe_wpisy', 0)} wpisów, {oc.get('nowe_alarmy', 0)} alarmów."
                + (f" Błąd odczytu issue: {oc['blad']}." if oc.get("blad") else "")])]


def kontrola_zdrowia(stan_pobrania: dict | None, bez_powiadomien: bool):
    import jakosc, tlumacz  # noqa: E402
    pob = stan_pobrania or {}
    plik = STRONA / "dane.json"
    dane_ts = dt.datetime.fromtimestamp(plik.stat().st_mtime, dt.timezone.utc).isoformat(timespec="minutes") if plik.exists() else None
    wynik = jakosc.zapisz_zdrowie(pob.get("ok"), pob.get("razem"), tlumacz._stan["bledy"], dane_ts)
    if wynik["nowy_incydent"]:
        print("INCYDENT ZDROWIA:", wynik["nowy_incydent"])
        if not bez_powiadomien:
            import koszty, poczta  # noqa: E402
            tekst = (f"Problem z działaniem aplikacji: {wynik['nowy_incydent']}.\n"
                     "Sprawdź log ostatnich przebiegów w zakładce Actions. Kolejny mail przyjdzie dopiero przy następnym incydencie.")
            if poczta.wyslij("Incydent: aplikacja działa nieprawidłowo", tekst,
                             poczta.ramka_tekstu(tekst, "WCZESNE OSTRZEŻENIE · INCYDENT"), odbiorcy=poczta.admin()):
                koszty.zapisz_mail("admin", "incydent zdrowia")
    elif wynik["koniec_incydentu"]:
        print("Incydent zdrowia zakończony")


def wyslij_raport_admin(w: dict):
    import koszty, poczta  # noqa: E402
    temat, tekst, html_ = poczta.zbuduj_admin(koszty.raport_7dni(), w.get("utrzymanie"), sekcje_admin(w))
    if poczta.wyslij(temat, tekst, html_, odbiorcy=poczta.admin()):
        koszty.zapisz_mail("admin", temat)


def utrzymaj_zrodla(zrodla, jakosc, zastosuj=True) -> dict:
    import utrzymanie  # noqa: E402
    wynik = utrzymanie.przeglad(zrodla, jakosc, wczytaj_json(PLIK_STAT, {}), teraz(), pobierz_kanal, data_wpisu,
                                wczytaj_yaml(PLIK_WSKAZNIKI).get("utrzymanie_zrodel"), zastosuj=zastosuj)
    for z in wynik["zmiany"]:
        print(f"Źródło {z['id']}: {z['typ']} {z['z']} -> {z['na']} ({z['powod']})")
    for u in wynik["uwagi"]:
        print("Uwaga:", u)
    if zastosuj and wynik["zmiany"]:
        zapisz_zrodla(zrodla)
        utrzymanie.zapisz_log(DANE / "zmiany_zrodel.jsonl", wynik["zmiany"])
    return wynik  # mail z przeglądem idzie w poniedziałkowym raporcie administracyjnym (wyslij_raport_admin)


def status_md(w: dict, slownik: "Slownik") -> str:
    """Karta statusu dla przeglądu portfolio (zapisywana co tydzień do main jako _state/status_auto.md)."""
    t, zb, pob = w["trend"], w["zbieznosc"], w.get("pobranie") or {}
    ost7 = [h for h in w["historia"] if not h["rek"]][-7:]
    awarie = [f"{zid} ({j['ostatni_blad']})" for zid, j in w["jakosc"].items() if j.get("ostatni_blad")]
    flagi = [f"{zid}: {', '.join(f for f in j['flagi'] if f != 'kanał nie działa')}" for zid, j in w["jakosc"].items()
             if any(f != "kanał nie działa" for f in j.get("flagi", []))]
    if not pob:
        zdrowie = "brak pobrania w tym przebiegu"
    else:
        zdrowie = "OK" if pob["ok"] >= 0.9 * max(1, pob["razem"]) else "UWAGA: mniej niż 90% kanałów działa"
    linie = [
        "# Status automatyczny: Wczesne ostrzeżenie", "",
        "> Plik nadpisywany przez workflow `wczesne-ostrzezenie` (poniedziałki rano i ręczne uruchomienia).",
        "> Czyta go `/portfolio-review`. Nie edytuj ręcznie.", "",
        "| Pole | Wartość |", "|------|---------|",
        f"| **Stan na** | {w['wygenerowano']} (UTC) |",
        f"| **Automatyzacja** | {zdrowie}; kanały {pob.get('ok', '–')}/{pob.get('razem', '–')} |",
        f"| **Poziom** | {w['prog']['nazwa']}, indeks {w['indeks']:.0f}/100 |",
        f"| **Trend** | wobec 7 dni: {strzalka(w['indeks'], t['sr_7'])}; wobec 30 dni: {strzalka(w['indeks'], t['sr_30'])}; dni historii: {t['dni_historii']} |",
        f"| **Spiętrzenie sygnałów** | {zb['nazwa']}" + (f" ({', '.join(slownik.kat[k]['nazwa'].lower() for k in zb['zbiezne'])})" if zb["zbiezne"] else "") + " |",
        f"| **Ostatnie 7 dni** | " + (", ".join(f"{h['dzien'][5:]}: {h['indeks']:.0f}" for h in ost7) or "brak") + " |",
        f"| **Alarm trendu** | {(w.get('trend_alarm') or {}).get('stan', '–')}: {(w.get('trend_alarm') or {}).get('opis', '')} |",
        f"| **Analogia 2021/22** | {sum(a['trafienie'] for a in w['analogia'])} z {len(w['analogia'])} |",
        f"| **Kanały nie działają** | {'; '.join(awarie) or 'brak'} |",
        f"| **Źródła do przeglądu** | {'; '.join(flagi) or 'brak'} |",
        f"| **Automatyczne zmiany źródeł** | " + ("; ".join(f"{z['nazwa']}: {z['z']} → {z['na']} ({z['powod']})" for z in (w.get('utrzymanie') or {}).get('zmiany', [])) or "brak w tym przebiegu") + " |",
        "",
    ]
    return "\n".join(linie)


def zapisz_skrot_md(w, slownik):
    p = DANE / "skroty" / f"{w['dzien']}.md"
    p.parent.mkdir(exist_ok=True)
    linie = [f"# Skrót dnia {w['dzien']}", "", *[f"- {s}" for s in w["skrot"]], "", "## Najważniejsze wiadomości", ""]
    for n in w["najwazniejsze"]:
        linie.append(f"- [{n['tytul']}]({n['link']}) ({', '.join(z for z, _ in n['zrodla'][:3])}; "
                     f"{', '.join(slownik.kat[k]['nazwa'].lower() for k in n['kategorie'])})")
    p.write_text("\n".join(linie) + "\n", encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(description="Wczesne ostrzeganie: Warszawa")
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("uruchom", help="pobierz, analizuj, zbuduj stronę, powiadom")
    u.add_argument("--bez-pobierania", action="store_true")
    u.add_argument("--bez-powiadomien", action="store_true")
    u.add_argument("--mail-skrot", action="store_true", help="wyślij skrót dnia mailem (zmienne SMTP_USER, SMTP_PASS, MAIL_DO)")
    u.add_argument("--harmonogram", action="store_true", help="skrót o godzinach z STATUS_GODZINY (Warszawa), przegląd źródeł w poniedziałek rano")
    u.add_argument("--znacznik-main", metavar="PLIK", help="utwórz plik, gdy rejestr źródeł i karta statusu mają iść do main")
    u.add_argument("--utrzymanie-zrodel", action="store_true", help="cotygodniowy przegląd źródeł według reguł (zmienia zrodla.yaml)")
    u.add_argument("--status-md", metavar="PLIK", help="zapisz kartę statusu dla przeglądu portfolio")
    u.add_argument("--podglad-maila", metavar="PLIK", help="zapisz HTML maila do pliku zamiast/obok wysyłki")
    z = sub.add_parser("zrodla", help="zarządzanie źródłami")
    z.add_argument("akcja", choices=["lista", "testuj", "dodaj", "ocen", "status", "przeglad"])
    z.add_argument("cel", nargs="?", help="URL (testuj) albo id źródła (ocen, status)")
    z.add_argument("nowy", nargs="?", help="nowy status (dla akcji status)")
    z.add_argument("--status"); z.add_argument("--min", choices=list("ABCDEF")); z.add_argument("--kraj")
    z.add_argument("--typ", default=None); z.add_argument("--id"); z.add_argument("--nazwa"); z.add_argument("--url")
    z.add_argument("--grupa"); z.add_argument("--jezyk", default="pl"); z.add_argument("--perspektywa", default="PL")
    z.add_argument("--wiarygodnosc", choices=list("ABCDEF"), default="F"); z.add_argument("--notatka"); z.add_argument("--powod")
    a = p.parse_args(argv)
    if a.cmd == "zrodla" and a.akcja == "dodaj":
        a.typ = a.typ or "media"
        a.kraj = a.kraj or "PL"
        if not (a.id and a.nazwa and a.url):
            p.error("dodaj wymaga --id, --nazwa i --url")
    return cmd_uruchom(a) if a.cmd == "uruchom" else cmd_zrodla(a)


if __name__ == "__main__":
    sys.exit(main())
