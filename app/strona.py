"""Strona dla znajomych w stylu retro-terminala obrony cywilnej (zielony luminofor, skanlinie).

Pliki: strona/index.html (pulpit), strona/metodyka.html (metodyka prostym językiem),
strona/artefakt.html (pulpit bez szkieletu dokumentu, do publikacji jako Artifact), strona/dane.json.
Projekt własny, inspirowany estetyką retro-futurystycznych komputerów naręcznych; bez znaków towarowych gier.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from html import escape as e
from pathlib import Path
from zoneinfo import ZoneInfo

from wersja import WERSJA  # noqa: E402

WAW = ZoneInfo("Europe/Warsaw")
STRONA = Path(__file__).resolve().parent.parent / "strona"
MIESIACE = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
            "września", "października", "listopada", "grudnia"]
TYP_OPIS = {"think-tank": "think tank", "agencja": "agencja", "media": "media", "media-publiczne": "media publiczne",
            "media-branzowe": "media branżowe", "rzad": "rząd", "osint": "OSINT", "agregator": "agregator"}
STATUS_OPIS = {"aktywne": "aktywne", "obserwacja": "na próbie", "monitoring": "podsłuch Kremla", "zablokowane": "zablokowane"}
# Lista źródeł na pulpicie: grupy według regionu i kraju (kolejność = kolejność na stronie).
REGIONY = [("Polska", ["PL"]), ("Kraje bałtyckie", ["LT", "LV", "EE"]), ("Kraje nordyckie", ["FI", "SE", "NO", "DK", "IS"]),
           ("Europa Zachodnia i UE", ["GB", "DE", "FR", "NL", "EU"]), ("Ukraina", ["UA"]), ("Stany Zjednoczone", ["US"]),
           ("Rosja (podsłuch propagandy)", ["RU"])]
KRAJE = {"PL": "Polska", "LT": "Litwa", "LV": "Łotwa", "EE": "Estonia", "FI": "Finlandia", "SE": "Szwecja", "NO": "Norwegia",
         "DK": "Dania", "IS": "Islandia", "GB": "Wielka Brytania", "DE": "Niemcy", "FR": "Francja", "NL": "Holandia",
         "EU": "Unia Europejska", "UA": "Ukraina", "US": "USA", "RU": "Rosja", "QA": "Katar"}
JEZYKI = {"pl": "polski", "en": "angielski", "lv": "łotewski", "lt": "litewski", "et": "estoński", "fi": "fiński",
          "ru": "rosyjski", "sv": "szwedzki", "no": "norweski", "da": "duński", "uk": "ukraiński", "de": "niemiecki", "fr": "francuski"}
BEZ_TLUMACZENIA = {"pl", "en"}


def region(kraj: str) -> tuple[int, str, int]:
    """(kolejność regionu, nazwa regionu, kolejność kraju w regionie); kraje spoza listy trafiają do „Pozostałe”."""
    for i, (nazwa, kraje) in enumerate(REGIONY):
        if kraj in kraje:
            return i, nazwa, kraje.index(kraj)
    return len(REGIONY), "Pozostałe", 0


def _opis_grupy(zr: list[dict]) -> str:
    """„4 źródła · szwedzki · tłumaczone na polski: szwedzki”."""
    jez = sorted({x.get("jezyk", "") for x in zr if x.get("jezyk")})
    tl = [JEZYKI.get(j, j) for j in jez if j not in BEZ_TLUMACZENIA]
    n = len(zr)
    return (f'{n} {"źródło" if n == 1 else "źródła" if 1 < n % 10 < 5 and not 11 < n % 100 < 15 else "źródeł"} · '
            + ", ".join(JEZYKI.get(j, j) for j in jez) + (f" · tłumaczone na polski: {', '.join(tl)}" if tl else ""))


def wiersze_zrodel_grupami(zrodla: list[dict], wiersz) -> list[str]:
    """Wiersze tabeli źródeł z nagłówkami regionu i kraju. `wiersz(z, reg)` zwraca <tr> jednego źródła."""
    kol = ["aktywne", "obserwacja", "monitoring", "zablokowane"]
    posort = sorted(zrodla, key=lambda z: (region(z["kraj"])[0], region(z["kraj"])[2], z["kraj"],
                                           kol.index(z["status"]), z["wiarygodnosc"], z["nazwa"]))
    wynik, akt_reg, akt_kraj = [], None, None
    for z in posort:
        _, reg, _ = region(z["kraj"])
        reg_zr = [x for x in zrodla if region(x["kraj"])[1] == reg]
        jeden_kraj = len({x["kraj"] for x in reg_zr}) == 1
        if reg != akt_reg:
            opis = f" · {_opis_grupy(reg_zr)}" if jeden_kraj else f" · {len(reg_zr)}"
            wynik.append(f'<tr class="reg" data-naglowek="r:{e(reg)}"><th colspan="9">{e(reg)}{e(opis)}</th></tr>')
            akt_reg, akt_kraj = reg, None
        if z["kraj"] != akt_kraj and not jeden_kraj:
            kraj_zr = [x for x in zrodla if x["kraj"] == z["kraj"]]
            wynik.append(f'<tr class="kraj" data-naglowek="k:{e(z["kraj"])}"><th colspan="9"><b>{e(KRAJE.get(z["kraj"], z["kraj"]))}</b>'
                         f' · {e(_opis_grupy(kraj_zr))}</th></tr>')
            akt_kraj = z["kraj"]
        wynik.append(wiersz(z, reg))
    return wynik
POZIOM_KLASA = {"zielony": "l0", "zolty": "l1", "pomaranczowy": "l2", "czerwony": "l3"}
FONTY = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=VT323&family=Share+Tech+Mono&display=swap">\n')

CSS = r"""
/* Układ: ekran terminala w obudowie; pasek zakładek u góry, licznik WW i zegar zagłady obok siebie, niżej panele. Jeden, celowo ciemny motyw. */
:root {
  --bg: #030a05; --case: #0c140e; --screen: #071a0e; --ph: #4dff91; --ph-2: #33d673; --ph-dim: #1d8a4b;
  --ph-faint: #0f3d22; --ink-inv: #021007; --line: #15502e;
  --f-display: "VT323", "Courier New", ui-monospace, monospace;
  --f-body: "Share Tech Mono", ui-monospace, "Courier New", monospace;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { background: var(--bg); }
body { background: var(--bg); color: var(--ph); font-family: var(--f-body); font-size: 15px; line-height: 1.55; margin: 0;
  text-shadow: 0 0 5px rgba(77, 255, 145, .35); }
body::after { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 50;
  background: repeating-linear-gradient(to bottom, rgba(0,0,0,0) 0 2px, rgba(0,0,0,.22) 2px 3px),
              radial-gradient(ellipse at center, rgba(0,0,0,0) 60%, rgba(0,0,0,.45) 100%); }
@media (prefers-reduced-motion: no-preference) {
  .flicker { animation: flicker 6s infinite steps(1); }
  @keyframes flicker { 0%, 96%, 100% { opacity: 1 } 97% { opacity: .82 } 98% { opacity: .95 } }
  .blink { animation: blink 1.1s infinite steps(1); }
  @keyframes blink { 50% { opacity: .25 } }
  .igla { transition: transform 1.2s cubic-bezier(.2, 1.4, .4, 1); }
}
.wrap { max-width: 1120px; margin: 0 auto; padding-block: 18px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 18px; }
a { color: var(--ph); text-decoration: underline; text-underline-offset: 3px; text-decoration-color: var(--ph-dim); }
a:hover { background: var(--ph); color: var(--ink-inv); text-shadow: none; }
a:focus-visible, select:focus-visible, input:focus-visible { outline: 2px dashed var(--ph); outline-offset: 2px; }
h1, h2, h3 { font-family: var(--f-display); font-weight: 400; margin: 0; line-height: 1; letter-spacing: .04em; text-wrap: balance; }
h2 { font-size: 1.9rem; text-transform: uppercase; }
h3 { font-size: 1.4rem; text-transform: uppercase; }
p { margin: 0; }
.dim { color: var(--ph-dim); }
.num { font-variant-numeric: tabular-nums; }
.etykieta { font-size: .75rem; letter-spacing: .14em; text-transform: uppercase; color: var(--ph-2); }

/* obudowa i pasek */
.obudowa { border: 2px solid var(--line); border-radius: 14px; background: var(--case); padding: 10px;
  box-shadow: inset 0 0 0 4px #08100a, 0 0 40px rgba(77,255,145,.06); }
.ekran { border-radius: 10px; background: radial-gradient(ellipse at 50% 30%, #0b2614 0%, var(--screen) 70%);
  border: 1px solid var(--ph-faint); padding-block: 14px 20px; padding-inline: clamp(12px, 3vw, 26px); display: grid; gap: 18px; min-width: 0; }
.belka { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 18px; }
.marka { display: flex; align-items: center; gap: 10px; }
.marka h1 { font-size: clamp(1.7rem, 4.5vw, 2.4rem); }
.marka .sub { font-size: .75rem; letter-spacing: .14em; color: var(--ph-2); }
.ikona { width: 1em; height: 1em; display: inline-block; vertical-align: -.12em; fill: currentColor; }
.marka .ikona { width: 42px; height: 42px; }
.zakladki { display: flex; flex-wrap: wrap; gap: 4px; border-bottom: 2px solid var(--ph-dim); }
.zakladki a { font-family: var(--f-display); font-size: 1.35rem; letter-spacing: .08em; text-decoration: none; padding: 2px 12px 0;
  border: 2px solid transparent; border-bottom: 0; color: var(--ph); }
.zakladki a.aktywna, .zakladki a:hover { border-color: var(--ph-dim); background: var(--ph-faint); color: var(--ph); }
.zegar-sys { font-size: .8rem; color: var(--ph-2); }

/* panele */
.panel { border: 1px solid var(--ph-dim); padding: 14px 16px; display: grid; gap: 12px; min-width: 0; position: relative; }
.panel > *, .lista li > * { min-width: 0; }
.lista a, .notatka, .meta span { overflow-wrap: anywhere; }
.panel > .tytul { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 4px 12px;
  border-bottom: 1px dashed var(--ph-faint); padding-bottom: 6px; }
.siatka { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 18px; }
@media (max-width: 820px) { .siatka { grid-template-columns: 1fr; } }

/* licznik WW */
.ww { display: grid; gap: 6px; justify-items: center; text-align: center; }
.ww > svg { width: 100%; max-width: 560px; height: auto; }
.ww svg text { fill: var(--ph); font-family: var(--f-display); }
.ww .poziom { font-family: var(--f-display); font-size: clamp(2.2rem, 7vw, 3.4rem); line-height: 1; text-transform: uppercase; }
.ww .opis { max-width: 46ch; }
.l3 .ww .poziom { background: var(--ph); color: var(--ink-inv); padding: 0 .3em; text-shadow: none; }

/* zegar zagłady */
.zz { display: grid; gap: 8px; justify-items: center; text-align: center; }
.zz > svg { width: 100%; max-width: 230px; height: auto; }
.tytul .ikona { width: 1.8rem; height: 1.8rem; }
.zz .czas { font-family: var(--f-display); font-size: 2.6rem; line-height: 1; }

/* kafle stanu */
.kafle { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.kafel { border: 1px solid var(--ph-faint); padding: 8px 10px; display: grid; gap: 2px; background: rgba(77,255,145,.03); }
.kafel .w { font-family: var(--f-display); font-size: 1.7rem; line-height: 1.05; }
.kafel.on { border-color: var(--ph); background: var(--ph-faint); }
.skrot { margin: 0; padding: 0; list-style: none; display: grid; gap: 6px; max-width: 90ch; }
.skrot li::before { content: "> "; color: var(--ph-2); }

/* wykres */
.wykres svg { width: 100%; height: auto; display: block; }
.wykres text { fill: var(--ph-2); font-family: var(--f-body); font-size: 11px; }

/* kategorie */
.kat { display: grid; gap: 8px; }
.kat-row { display: grid; grid-template-columns: minmax(0, 17rem) minmax(0, 1fr) 7.5rem; gap: 12px; align-items: center; }
.bar { height: 14px; border: 1px solid var(--ph-dim); padding: 2px; }
.bar i { display: block; height: 100%; background: repeating-linear-gradient(90deg, var(--ph) 0 7px, transparent 7px 9px); }
.bar i.neg { background: repeating-linear-gradient(90deg, var(--ph-dim) 0 7px, transparent 7px 9px); }
.grupy { font-size: .8rem; text-align: right; }
.grupy.zb { background: var(--ph); color: var(--ink-inv); text-shadow: none; padding: 0 4px; }
@media (max-width: 640px) { .kat-row { grid-template-columns: 1fr 6.5rem; } .kat-row .bar { grid-column: 1 / -1; grid-row: 2; } }

/* wiadomości i analogia */
.lista { list-style: none; margin: 0; padding: 0; display: grid; }
.lista li { padding: 10px 0; border-top: 1px dashed var(--ph-faint); display: grid; gap: 4px; min-width: 0; }
.lista li:first-child { border-top: 0; }
.lista .meta { font-size: .8rem; color: var(--ph-2); display: flex; flex-wrap: wrap; gap: 2px 12px; }
.chip { font-size: .72rem; border: 1px solid var(--ph-dim); padding: 0 6px; margin: 0 4px 3px 0; display: inline-block; max-width: 100%; }
.analog li { grid-template-columns: 2.2rem 8.5rem minmax(0, 1fr); column-gap: 12px; }
.analog .znak { font-family: var(--f-display); font-size: 1.4rem; width: 1.8rem; height: 1.8rem; display: grid; place-items: center;
  border: 1px solid var(--ph-dim); }
.analog li.tak .znak { background: var(--ph); color: var(--ink-inv); text-shadow: none; }
.analog .kiedy { font-size: .8rem; color: var(--ph-2); padding-top: 3px; }
@media (max-width: 640px) { .analog li { grid-template-columns: 2.2rem minmax(0, 1fr); } .analog .kiedy, .analog .tresc { grid-column: 2; } }

/* źródła */
.filtry { display: flex; flex-wrap: wrap; gap: 10px 14px; align-items: end; }
.filtry label { display: grid; gap: 3px; font-size: .72rem; letter-spacing: .1em; text-transform: uppercase; color: var(--ph-2); }
.filtry select, .filtry input { font: inherit; font-size: .9rem; padding: 4px 8px; border: 1px solid var(--ph-dim); border-radius: 0;
  background: var(--screen); color: var(--ph); min-width: 0; }
.tabela { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .84rem; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px dashed var(--ph-faint); vertical-align: top; }
th { font-weight: 400; font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; color: var(--ph-2); white-space: nowrap; }
td.num { white-space: nowrap; }
.ocena { display: inline-block; width: 1.6rem; text-align: center; border: 1px solid var(--ph-dim); }
.ocena-A, .ocena-B { background: var(--ph); color: var(--ink-inv); text-shadow: none; }
.ocena-E, .ocena-D { text-decoration: line-through; }
.notatka { color: var(--ph-dim); font-size: .78rem; max-width: 44ch; }
.st-zablokowane { text-decoration: line-through; color: var(--ph-dim); }
.flaga { font-size: .75rem; }
.flaga::before { content: "! "; }
tr.reg th { font-size: .82rem; color: var(--ph); padding-top: 16px; border-bottom: 1px solid var(--ph-dim); }
tr.kraj th { color: var(--ph-2); padding-left: 14px; text-transform: none; letter-spacing: .04em; }
tr.kraj th b { font-weight: 400; color: var(--ph); }

/* proza (metodyka) */
.proza { display: grid; gap: 12px; max-width: 74ch; }
.proza ul, .proza ol { margin: 0; padding-left: 1.3em; display: grid; gap: 6px; }
.proza b { font-weight: 400; background: var(--ph-faint); padding: 0 3px; }
.tab-prosta { overflow-x: auto; }
footer { font-size: .78rem; color: var(--ph-2); display: flex; flex-wrap: wrap; gap: 6px 18px; justify-content: space-between;
  border-top: 1px dashed var(--ph-faint); padding-top: 10px; }
"""

JS = r"""
(function () {
  var f = { s: document.getElementById('f-status'), o: document.getElementById('f-ocena'), k: document.getElementById('f-kraj'),
            t: document.getElementById('f-typ'), q: document.getElementById('f-szukaj') };
  if (!f.s) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('#tab-zrodla tbody tr[data-status]'));
  var naglowki = Array.prototype.slice.call(document.querySelectorAll('#tab-zrodla tbody tr[data-naglowek]'));
  var licznik = document.getElementById('f-licznik');
  var rang = 'ABCDEF';
  function filtruj() {
    var n = 0, q = (f.q.value || '').toLowerCase(), widoczne = {};
    rows.forEach(function (r) {
      var ok = (!f.s.value || r.dataset.status === f.s.value)
        && (!f.o.value || rang.indexOf(r.dataset.ocena) <= rang.indexOf(f.o.value))
        && (!f.k.value || r.dataset.kraj === f.k.value)
        && (!f.t.value || r.dataset.typ === f.t.value)
        && (!q || (r.dataset.szukaj + ' ' + r.textContent).toLowerCase().indexOf(q) >= 0);
      r.hidden = !ok;
      if (ok) { n++; widoczne['k:' + r.dataset.kraj] = 1; widoczne['r:' + r.dataset.region] = 1; }
    });
    naglowki.forEach(function (h) { h.hidden = !widoczne[h.dataset.naglowek]; });
    licznik.textContent = n + ' / ' + rows.length;
  }
  Object.keys(f).forEach(function (k) { f[k].addEventListener('input', filtruj); });
  filtruj();
})();
"""


# ---------------------------------------------------------------- ikony (rysowane, bez plików)

def _sektor(r1, r2, a1, a2):
    def p(r, a):
        return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
    x1, y1 = p(r1, a1); x2, y2 = p(r2, a1); x3, y3 = p(r2, a2); x4, y4 = p(r1, a2)
    return f"M{x1:.3f},{y1:.3f} L{x2:.3f},{y2:.3f} A{r2},{r2} 0 0 1 {x3:.3f},{y3:.3f} L{x4:.3f},{y4:.3f} A{r1},{r1} 0 0 0 {x1:.3f},{y1:.3f} Z"


def ikona_radiacja(klasa="ikona", tytul="Znak promieniowania"):
    sciezki = "".join(f'<path d="{_sektor(0.24, 0.95, a, a + 60)}"/>' for a in (-120, 0, 120))
    return (f'<svg class="{klasa}" viewBox="-1 -1 2 2" role="img" aria-label="{e(tytul)}">'
            f'<circle r="0.98" fill="none" stroke="currentColor" stroke-width="0.04"/>{sciezki}<circle r="0.15"/></svg>')


def ikona_schron(klasa="ikona", tytul="Znak schronu"):
    tr = []
    for a in (90, 210, 330):
        ra = math.radians(a)
        cx, cy = 0.55 * math.cos(ra), 0.55 * math.sin(ra)
        pts = []
        for d in (0, 120, 240):
            rb = math.radians(a + 180 + d)
            pts.append(f"{cx + 0.36 * math.cos(rb):.3f},{cy + 0.36 * math.sin(rb):.3f}")
        tr.append(f'<polygon points="{" ".join(pts)}"/>')
    return (f'<svg class="{klasa}" viewBox="-1 -1 2 2" role="img" aria-label="{e(tytul)}">'
            f'<circle r="0.98" fill="none" stroke="currentColor" stroke-width="0.06"/>{"".join(tr)}</svg>')


def ikona_grzyb(klasa="ikona", tytul="Grzyb atomowy"):
    return (f'<svg class="{klasa}" viewBox="0 0 64 64" role="img" aria-label="{e(tytul)}">'
            '<circle cx="22" cy="20" r="11"/><circle cx="34" cy="14" r="13"/><circle cx="45" cy="21" r="10"/>'
            '<ellipse cx="33" cy="27" rx="20" ry="6"/><rect x="28" y="28" width="10" height="22" rx="3"/>'
            '<ellipse cx="33" cy="36" rx="12" ry="3.2"/><ellipse cx="33" cy="54" rx="22" ry="6"/></svg>')


def ikona_maska(klasa="ikona", tytul="Maska przeciwgazowa"):
    return (f'<svg class="{klasa}" viewBox="0 0 64 64" role="img" aria-label="{e(tytul)}">'
            '<path d="M32 6c-13 0-22 9-22 22 0 9 4 16 10 20l4 8h16l4-8c6-4 10-11 10-20C54 15 45 6 32 6z" fill="none" stroke="currentColor" stroke-width="4"/>'
            '<circle cx="23" cy="26" r="6"/><circle cx="41" cy="26" r="6"/><rect x="25" y="40" width="14" height="14" rx="4"/></svg>')


# ---------------------------------------------------------------- elementy pulpitu

def data_pl(iso: str) -> str:
    d = dt.datetime.fromisoformat(iso).astimezone(WAW)
    return f"{d.day} {MIESIACE[d.month - 1]} {d.year}, {d:%H:%M}"


def sekundy_do_polnocy(indeks: float) -> int:
    """Zegar zagłady wersji warszawskiej: WW 0 = 15 minut do północy, WW 100 = północ."""
    return round(900 * (1 - max(0.0, min(100.0, indeks)) / 100))


def licznik_ww(indeks: float, progi: list[dict]) -> str:
    cx, cy, r = 200, 190, 150
    def pkt(v, rr):
        a = math.radians(180 + 180 * v / 100)
        return cx + rr * math.cos(a), cy + rr * math.sin(a)
    out = ['<svg viewBox="-45 0 490 232" role="img" aria-label="Licznik współczynnika wpierdolu: '
           f'{indeks:.0f} na 100">']
    granice = [p["od"] for p in progi] + [100]
    for i, p in enumerate(progi):
        a, b = granice[i], granice[i + 1]
        x1, y1 = pkt(a, r); x2, y2 = pkt(b, r)
        out.append(f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 0 1 {x2:.1f},{y2:.1f}" fill="none" stroke="var(--ph)" '
                   f'stroke-width="18" opacity="{0.22 + 0.26 * i:.2f}"/>')
        srodek = (a + b) / 2
        tx, ty = pkt(srodek, r + 20)
        kotwica = "end" if srodek < 40 else ("start" if srodek > 60 else "middle")
        out.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{kotwica}" font-size="15">{e(p.get("luzno", p["nazwa"]).upper())}</text>')
    for v in range(0, 101, 5):
        x1, y1 = pkt(v, r - 13); x2, y2 = pkt(v, r - (24 if v % 10 == 0 else 19))
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="var(--ph-2)" stroke-width="{2 if v % 10 == 0 else 1}"/>')
    for v in granice:
        tx, ty = pkt(v, r - 38)
        out.append(f'<text x="{tx:.1f}" y="{ty + 5:.1f}" text-anchor="middle" font-size="18">{v}</text>')
    kat = -90 + 180 * max(0, min(100, indeks)) / 100
    out.append(f'<g class="igla" style="transform-origin:{cx}px {cy}px;transform:rotate({kat:.1f}deg)">'
               f'<polygon points="{cx - 5},{cy} {cx + 5},{cy} {cx},{cy - r + 30}" fill="var(--ph)"/></g>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="12" fill="var(--screen)" stroke="var(--ph)" stroke-width="3"/>')
    out.append(f'<text x="{cx}" y="{cy - 46}" text-anchor="middle" font-size="64">{indeks:.0f}</text>')
    out.append("</svg>")
    return "".join(out)


def zegar_zaglady(indeks: float) -> tuple[str, str]:
    s = sekundy_do_polnocy(indeks)
    minuty = s / 60
    cx = cy = 100
    out = ['<svg viewBox="0 0 200 200" role="img" aria-label="Zegar zagłady: '
           f'{s // 60} minut {s % 60} sekund do północy">',
           f'<circle cx="{cx}" cy="{cy}" r="92" fill="none" stroke="var(--ph)" stroke-width="3"/>',
           # ćwiartka przed północą zaciemniona: tam chodzi wskazówka
           f'<path d="M{cx},{cy} L{cx},{cy - 88} A88,88 0 0 0 {cx - 88},{cy} Z" fill="var(--ph-faint)"/>']
    for i in range(60):
        a = math.radians(i * 6 - 90)
        r1 = 80 if i % 5 else 72
        out.append(f'<line x1="{cx + r1 * math.cos(a):.1f}" y1="{cy + r1 * math.sin(a):.1f}" x2="{cx + 88 * math.cos(a):.1f}" '
                   f'y2="{cy + 88 * math.sin(a):.1f}" stroke="var(--ph-2)" stroke-width="{3 if i % 5 == 0 else 1}"/>')
    am = math.radians((60 - minuty) * 6 - 90)
    ah = math.radians((11 + (60 - minuty) / 60) * 30 - 90)
    out.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + 52 * math.cos(ah):.1f}" y2="{cy + 52 * math.sin(ah):.1f}" stroke="var(--ph)" stroke-width="6" stroke-linecap="round"/>')
    out.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + 78 * math.cos(am):.1f}" y2="{cy + 78 * math.sin(am):.1f}" stroke="var(--ph)" stroke-width="3" stroke-linecap="round"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="var(--ph)"/>')
    out.append("</svg>")
    return "".join(out), f"{s // 60} MIN {s % 60:02d} S"


def trend_kafel(etykieta: str, teraz: float, ref) -> str:
    if ref is None:
        return f'<div class="kafel"><span class="etykieta">{e(etykieta)}</span><span class="w dim">BRAK DANYCH</span></div>'
    d = teraz - ref
    slowo = "bez zmian" if abs(d) < 3 else ("wzrost" if d > 0 else "spadek")
    znak = "=" if abs(d) < 3 else ("▲" if d > 0 else "▼")
    return (f'<div class="kafel{" on" if d >= 3 else ""}"><span class="etykieta">{e(etykieta)}</span>'
            f'<span class="w num">{znak} {d:+.0f}</span><span class="dim" style="font-size:.78rem">{slowo}, średnio {ref:.0f}</span></div>')


def wykres(historia: list[dict], progi: list[dict]) -> str:
    W, H, L, R, T, B = 800, 230, 34, 12, 12, 26
    pw, ph = W - L - R, H - T - B
    hist = historia[-90:]
    if not hist:
        return '<p class="dim">Historia pojawi się po pierwszym dniu działania.</p>'
    def x(i):
        return L + (pw * i / max(1, len(hist) - 1))
    def y(v):
        return T + ph * (1 - v / 100)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Współczynnik wpierdolu w ostatnich {len(hist)} dniach">']
    granice = [p["od"] for p in progi] + [100]
    for v in range(0, 101, 10):
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="var(--ph-faint)" stroke-width="1"/>')
    for v in granice:
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="var(--ph-dim)" stroke-width="1" stroke-dasharray="4 4"/>')
        out.append(f'<text x="{L - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    pts = [(x(i), y(h["indeks"])) for i, h in enumerate(hist)]
    if len(pts) > 1:
        area = f"M{pts[0][0]:.1f},{y(0):.1f} " + " ".join(f"L{a:.1f},{b:.1f}" for a, b in pts) + f" L{pts[-1][0]:.1f},{y(0):.1f} Z"
        out.append(f'<path d="{area}" fill="var(--ph)" opacity=".10"/>')
        out.append('<polyline fill="none" stroke="var(--ph)" stroke-width="2" points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + '"/>')
    for i, (h, (a, b)) in enumerate(zip(hist, pts)):
        ost = i == len(hist) - 1
        fill = "var(--screen)" if h["rek"] else "var(--ph)"
        r = 5 if ost else 3
        if h["alarm"] >= 2:
            out.append(f'<rect x="{a - 5:.1f}" y="{b - 5:.1f}" width="10" height="10" fill="var(--ph)"/>')
        out.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{r}" fill="{fill}" stroke="var(--ph)" stroke-width="1.5">'
                   f'<title>{h["dzien"]}: {h["indeks"]:.0f}{" (odtworzone)" if h["rek"] else ""}</title></circle>')
    a, b = pts[-1]
    out.append(f'<text x="{min(a, W - R - 4):.1f}" y="{b - 10:.1f}" text-anchor="end" style="fill:var(--ph);font-size:14px">{hist[-1]["indeks"]:.0f}</text>')
    for i in sorted({0, len(hist) // 2, len(hist) - 1}):
        d = dt.date.fromisoformat(hist[i]["dzien"])
        anchor = "start" if i == 0 else ("end" if i == len(hist) - 1 else "middle")
        out.append(f'<text x="{x(i):.1f}" y="{H - 6}" text-anchor="{anchor}">{d.day} {MIESIACE[d.month - 1][:3]}</text>')
    out.append("</svg>")
    return "".join(out)


def naglowek(aktywna: str, wygenerowano: str) -> str:
    baza = "" if aktywna == "pulpit" else "./"  # na pulpicie kotwice, z metodyki powrót do strony głównej (działa też w Artifact)
    zakl = [("pulpit", f"{baza}#stan", "STAN"), ("pulpit-syg", f"{baza}#sygnaly", "SYGNAŁY"),
            ("pulpit-wiad", f"{baza}#wiadomosci", "WIADOMOŚCI"), ("pulpit-an", f"{baza}#analogia", "ANALOGIA 2022"),
            ("pulpit-zr", f"{baza}#zrodla", "ŹRÓDŁA"), ("pulpit-skan", f"{baza}#skan", "ZLEĆ SKAN"),
            ("pulpit-zg", f"{baza}#zgloszenia", "ZGŁOSZENIA"), ("pulpit-jak", f"{baza}#jakosc", "JAKOŚĆ"),
            ("metodyka", "metodyka.html", "METODYKA")]
    linki = "".join(f'<a href="{h}" class="{"aktywna" if k == aktywna else ""}">{t}</a>' for k, h, t in zakl)
    return (f'<div class="belka"><div class="marka">{ikona_radiacja("ikona flicker")}'
            f'<div><h1>WCZESNE OSTRZEŻENIE</h1><div class="sub">TERMINAL OBRONY CYWILNEJ · WARSZAWA · MODEL WW-3000</div></div></div>'
            f'<div class="zegar-sys num">OSTATNI ODCZYT: {e(data_pl(wygenerowano))}</div></div>'
            f'<nav class="zakladki" aria-label="Zakładki">{linki}</nav>')


def stopka(n_zrodel: int) -> str:
    return (f'<footer><span>{ikona_schron()} Prywatne narzędzie znajomych, nie komunikat władz. Oficjalne alerty: '
            f'<a href="https://www.gov.pl/web/rcb" target="_blank" rel="noopener">Rządowe Centrum Bezpieczeństwa</a>.</span>'
            f'<span>{n_zrodel} źródeł · odczyt co godzinę · <a href="metodyka.html#telefon">ikona na telefon i maile</a> · '
            f'<a href="metodyka.html">jak to działa i jak zgłosić błąd</a> · '
            f'<a href="https://github.com/Climbat1ze/wczesne-ostrzezenie/blob/main/CHANGELOG.md" target="_blank" rel="noopener">wersja {e(WERSJA)}</a></span></footer>')


def dokument(tytul: str, tresc: str, skrypt: str = "") -> str:
    import ikony  # noqa: E402
    glowa = (f'<title>{e(tytul)}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
             f'{ikony.GLOWA}{FONTY}<style>{CSS}{CSS_V2}</style>\n')
    return glowa, tresc + (f"<script>{skrypt}</script>" if skrypt else "")


def zapisz_pelny(nazwa: str, glowa: str, cialo: str):
    (STRONA / nazwa).write_text(
        '<!doctype html>\n<html lang="pl">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Codzienny odczyt sygnałów zagrożenia wobec Polski i Bałtów z ocenionych źródeł.">\n'
        + glowa + '</head>\n<body>\n' + cialo + '\n</body>\n</html>\n', encoding="utf-8")


# ---------------------------------------------------------------- pulpit

def zbuduj(w: dict, zrodla: list[dict], slownik) -> None:
    STRONA.mkdir(exist_ok=True)
    import samouczenie  # noqa: E402
    repo = samouczenie.repo()
    n_szukaj = zapisz_szukaj(zrodla)
    print(f"Strona: szukaj.json, {n_szukaj} nagłówków z 3 dni")
    import ikony  # noqa: E402
    ikony.zapisz(STRONA)  # ikona na pulpit telefonu i manifest (deterministyczne, ok. 0,2 s)
    prog, kat, zb, t = w["prog"], slownik.kat, w["zbieznosc"], w["trend"]
    poz = POZIOM_KLASA[prog["kolor"]]
    zegar_svg, zegar_txt = zegar_zaglady(w["indeks"])
    ta = w.get("trend_alarm") or {}
    kryt = w.get("krytyczne") or []
    traf = sum(x["trafienie"] for x in w["analogia"])

    wiersze_kat = []
    for k, v in sorted(kat.items(), key=lambda kv: (kv[1]["waga"] <= 0, -kv[1]["waga"], kv[1]["nazwa"])):
        n = w["natezenie"].get(k, 0)
        g = zb["kategorie"].get(k, {}).get("grupy")
        if g is None:
            g_txt = '<span class="grupy dim">obniża WW</span>' if v["waga"] < 0 else '<span class="grupy dim">tło</span>'
        else:
            g_txt = f'<span class="grupy{" zb" if g >= 3 else ""}">{g} REDAKCJI / 72 H</span>'
        wiersze_kat.append(
            f'<div class="kat-row"><div><div>{e(v["nazwa"])}</div><div class="dim" style="font-size:.72rem">WAGA {v["waga"]:+d}</div></div>'
            f'<div class="bar" title="{n * 100:.0f}% skali"><i class="{"neg" if v["waga"] < 0 else ""}" style="width:{n * 100:.0f}%"></i></div>{g_txt}</div>')

    news = []
    for n in w["najwazniejsze"]:
        chips = "".join(f'<span class="chip">{e(kat[k]["nazwa"])}</span>' for k in n["kategorie"])
        zr = ", ".join(f'<a href="{e(l)}" rel="noopener" target="_blank">{e(z)}</a>' for z, l in n["zrodla"][:4])
        tl = f' <span class="dim" style="font-size:.75rem" title="{e(n.get("oryginal") or "")}">[TŁUM. Z {e(n["jezyk"].upper())}]</span>' if n.get("jezyk") else ""
        news.append(f'<li><div><a href="{e(n["link"])}" rel="noopener" target="_blank">{e(n["tytul"])}</a>{tl}</div>'
                    f'<div class="meta"><span>{zr}</span><span class="num">{data_pl(n["data"])}</span>'
                    f'<span>{n["grup"]} {"redakcja" if n["grup"] == 1 else "redakcje" if n["grup"] < 5 else "redakcji"}</span></div><div>{chips}</div></li>')
    news_html = "".join(news) or '<li class="dim">Cisza w eterze: brak wiadomości o Polsce i Bałtach z trafieniem wskaźników w 24 h.</li>'

    an = []
    for a in w["analogia"]:
        przyk = "; ".join(f'<a href="{e(p["link"])}" target="_blank" rel="noopener">{e(p["tytul"][:90])}</a> ({e(p["wydawca"])})' for p in a["przyklady"])
        dzis = (f'DZIŚ: {a["grup"]} {"redakcje" if a["grup"] < 5 else "redakcji"} w 30 dniach. {przyk}' if a["grup"] else "DZIŚ: brak odpowiednika wobec Polski, Bałtów i krajów nordyckich.")
        if a.get("odrzucone"):
            dzis += (' Model odrzucił 1 wiadomość, która pasowała słowami, ale nie sensem.' if a["odrzucone"] == 1 else
                     f' Model odrzucił {a["odrzucone"]} wiadomości, które pasowały słowami, ale nie sensem.')
        if a.get("niezweryfikowane"):
            dzis += f' {a["niezweryfikowane"]} bez sprawdzenia modelem.'
        pow_ = "; ".join(p["powod"] for p in a["przyklady"] if p.get("powod"))
        if pow_:
            dzis += f' Dlaczego pasuje: {e(pow_)}'
        an.append(f'<li class="{"tak" if a["trafienie"] else "nie"}"><span class="znak" aria-label="{"jest odpowiednik" if a["trafienie"] else "brak"}">{"!" if a["trafienie"] else "·"}</span>'
                  f'<span class="kiedy">{e(a["kiedy"])}</span><div class="tresc"><div>{e(a["co"])}</div><div class="dim" style="font-size:.82rem">{dzis}</div></div></li>')

    jak = w["jakosc"]
    def proc(v):
        return "–" if v is None else f"{v * 100:.0f}%"
    def wiersz_zrodla(z, reg):
        j = jak.get(z["id"], {})
        flagi = "".join(f'<div class="flaga">{e(f)}</div>' for f in j.get("flagi", []))
        jez = z.get("jezyk", "")
        jez_opis = JEZYKI.get(jez, jez) + ("" if jez in BEZ_TLUMACZENIA or not jez else " → PL")
        return (
            f'<tr data-status="{e(z["status"])}" data-ocena="{e(z["wiarygodnosc"])}" data-kraj="{e(z["kraj"])}" data-typ="{e(z["typ"])}"'
            f' data-region="{e(reg)}" data-szukaj="{e(KRAJE.get(z["kraj"], z["kraj"]) + " " + reg)}">'
            f'<td><a href="{e(z["url"])}" target="_blank" rel="noopener">{e(z["nazwa"])}</a><div class="notatka">{e(z.get("notatka", ""))}</div></td>'
            f'<td>{e(TYP_OPIS.get(z["typ"], z["typ"]))}</td><td class="num">{e(z["kraj"])}</td><td>{e(jez_opis)}</td>'
            f'<td><span class="ocena ocena-{e(z["wiarygodnosc"])}">{e(z["wiarygodnosc"])}</span></td>'
            f'<td class="st-{e(z["status"])}">{e(STATUS_OPIS[z["status"]])}</td>'
            f'<td class="num">{proc(j.get("krzykliwosc"))}</td><td class="num">{proc(j.get("potwierdzalnosc"))}</td><td>{flagi}</td></tr>')
    wiersze_zr = wiersze_zrodel_grupami(zrodla, wiersz_zrodla)
    def opcje(pole, opis=None):
        return "".join(f'<option value="{e(v)}">{e((opis or {}).get(v, v))}</option>' for v in sorted({z[pole] for z in zrodla}))
    n_akt = sum(z["status"] == "aktywne" for z in zrodla)
    pob = w.get("pobranie") or {}

    kafle = (
        f'<div class="kafel{" on" if zb["poziom"] else ""}"><span class="etykieta">Spiętrzenie sygnałów</span>'
        f'<span class="w {"blink" if zb["poziom"] >= 2 else ""}">{e(zb["nazwa"].upper())}</span>'
        f'<span class="dim" style="font-size:.78rem">{len(zb["zbiezne"])} kategorii z 3+ redakcjami</span></div>'
        f'<div class="kafel{" on" if kryt else ""}"><span class="etykieta">Sygnały krytyczne</span>'
        f'<span class="w {"blink" if kryt else ""}">{len(kryt) or "BRAK"}</span>'
        f'<span class="dim" style="font-size:.78rem">{e("; ".join(k["nazwa"] for k in kryt) or "ewakuacje, mobilizacja, art. 4/5")}</span></div>'
        f'<div class="kafel{" on" if ta.get("stan") == "alarm" else ""}"><span class="etykieta">Alarm trendu</span>'
        f'<span class="w">{ {"alarm": "WŁĄCZONY", "norma": "NORMA", "zbieram": "KALIBRACJA"}.get(ta.get("stan"), "–") }</span>'
        f'<span class="dim" style="font-size:.78rem">{e(ta.get("opis", ""))}</span></div>'
        f'<div class="kafel{" on" if traf >= 5 else ""}"><span class="etykieta">Analogia 2021/22</span>'
        f'<span class="w num">{traf} / {len(w["analogia"])}</span><span class="dim" style="font-size:.78rem">zdarzeń sprzed 24.02.2022 ma dziś odpowiednik u nas</span></div>'
        + trend_kafel("Wobec wczoraj", w["indeks"], t["wczoraj"])
        + trend_kafel("Wobec 7 dni", w["indeks"], t["sr_7"])
        + trend_kafel("Wobec 30 dni", w["indeks"], t["sr_30"]))

    tresc = f"""
<div class="wrap" id="pulpit" data-repo="{e(repo)}"><div class="obudowa"><div class="ekran">
{naglowek("pulpit", w["wygenerowano"])}

<section id="stan" class="siatka {poz}">
  <div class="panel ww">
    <div class="tytul" style="width:100%"><h2>Współczynnik wpierdolu</h2><span class="etykieta">aka fuck-o-meter</span></div>
    {licznik_ww(w["indeks"], slownik.progi)}
    <div class="poziom">{e(prog.get("luzno", prog["nazwa"]))}</div>
    <p class="opis">{e(prog.get("luzno_opis", prog["opis"]))} <span class="dim">Oficjalnie: {e(prog["nazwa"].lower())}. {e(prog["opis"])}</span></p>
  </div>
  <div class="panel zz">
    <div class="tytul" style="width:100%"><h2>Zegar zagłady</h2>{ikona_grzyb("ikona")}</div>
    {zegar_svg}
    <div class="czas num">{zegar_txt}</div>
    <p class="etykieta">do północy · wersja warszawska</p>
    <p class="dim" style="font-size:.8rem">WW 0 to kwadrans do północy, WW 100 to północ. Przelicznik w <a href="metodyka.html#zegar">metodyce</a>.</p>
  </div>
</section>

<section class="panel">
  <div class="tytul"><h3>Odczyt stanu</h3><span class="etykieta">{ikona_maska()} pakiet przetrwania</span></div>
  <div class="kafle">{kafle}</div>
  <div><div class="etykieta" style="margin-bottom:6px">Skrót dnia</div><ul class="skrot">{"".join(f"<li>{e(s)}</li>" for s in w["skrot"])}</ul></div>
</section>

<section class="panel wykres">
  <div class="tytul"><h3>WW w czasie</h3><span class="etykieta">ostatnie {min(90, len(w["historia"]))} dni</span></div>
  {wykres(w["historia"], slownik.progi)}
  <p class="dim" style="font-size:.8rem">Puste kółka: dni odtworzone z archiwum kanałów przy starcie (niepełne). Kwadrat: dzień z ostrzeżeniem lub alarmem spiętrzenia.</p>
</section>

<section id="sygnaly" class="panel">
  <div class="tytul"><h3>Sygnały według kategorii</h3><span class="etykieta">24 h natężenie · 72 h redakcje</span></div>
  <p class="dim" style="font-size:.82rem">Pasek: ile wiadomości z tej kategorii w 24 h, ważone oceną źródła i tym, czy dotyczą Polski lub Bałtów. Prawa kolumna: ile niezależnych redakcji z oceną A–C pisało o tym w 72 h. Od 3 redakcji kategoria się świeci.</p>
  <div class="kat">{"".join(wiersze_kat)}</div>
</section>

<section id="wiadomosci" class="panel">
  <div class="tytul"><h3>Najważniejsze wiadomości, 24 h</h3><span class="etykieta">tylko Polska, Bałtyk, Białoruś, NATO</span></div>
  <ul class="lista">{news_html}</ul>
</section>

<section id="analogia" class="panel">
  <div class="tytul"><h3>Analogia do zimy 2021/22</h3><span class="etykieta">{traf} z {len(w["analogia"])} świeci</span></div>
  <p class="dim" style="font-size:.82rem">Zdarzenia, które poprzedziły atak na Ukrainę 24.02.2022. Znak „!”: w 30 dniach min. 2 niezależne redakcje opisały odpowiednik wobec Polski, Bałtów lub krajów nordyckich, a model sprawdził, czy zgadza się strona (kto działa, wobec kogo), nie tylko słowa. Jeden znak nic nie znaczy; liczy się kilka naraz.</p>
  <ul class="lista analog">{"".join(an)}</ul>
</section>

<section id="zrodla" class="panel">
  <div class="tytul"><h3>Źródła</h3><span class="etykieta">{n_akt} aktywnych · {len(zrodla)} w rejestrze · kanały {pob.get("ok", "–")}/{pob.get("razem", "–")}</span></div>
  <p class="dim" style="font-size:.82rem">Ocena A–E według skali wywiadu NATO. Krzykliwość: odsetek tytułów z wykrzyknikami i słowami typu „szok”. Potwierdzalność: odsetek alarmowych wiadomości źródła, które w 48 h opisała inna wiarygodna redakcja. Szczegóły w <a href="metodyka.html#zrodla">metodyce</a>.</p>
  <div class="filtry">
    <label for="f-status">Status<select id="f-status"><option value="">wszystkie</option>{opcje("status", STATUS_OPIS)}</select></label>
    <label for="f-ocena">Ocena min.<select id="f-ocena"><option value="">dowolna</option>{"".join(f'<option value="{x}">{x}</option>' for x in "ABCDE")}</select></label>
    <label for="f-kraj">Kraj<select id="f-kraj"><option value="">wszystkie</option>{opcje("kraj", KRAJE)}</select></label>
    <label for="f-typ">Typ<select id="f-typ"><option value="">wszystkie</option>{opcje("typ", TYP_OPIS)}</select></label>
    <label for="f-szukaj">Szukaj<input id="f-szukaj" type="search" placeholder="np. LRT, Szwecja, nordyckie"></label>
    <span class="num etykieta" id="f-licznik" style="padding-bottom:6px"></span>
  </div>
  <div class="tabela"><table id="tab-zrodla"><thead><tr><th>Źródło</th><th>Typ</th><th>Kraj</th><th>Język</th><th>Ocena</th><th>Status</th><th>Krzyk</th><th>Potw.</th><th>Uwagi</th></tr></thead>
  <tbody>{"".join(wiersze_zr)}</tbody></table></div>
</section>

{sekcje_v2(w, repo)}

{stopka(len(zrodla))}
</div></div></div>
"""
    glowa, cialo = dokument("Wczesne Ostrzeżenie Warszawa", tresc, JS + JS_V2)
    (STRONA / "artefakt.html").write_text(glowa + cialo, encoding="utf-8")
    zapisz_pelny("index.html", glowa, cialo)
    zbuduj_metodyke(w, zrodla, slownik)
    dane = {k: w[k] for k in ("wygenerowano", "indeks", "prog", "trend", "natezenie", "skrot", "historia")}
    dane["wersja"] = WERSJA
    dane["zbieznosc"] = {"poziom": zb["poziom"], "nazwa": zb["nazwa"], "zbiezne": zb["zbiezne"]}
    dane["sekundy_do_polnocy"] = sekundy_do_polnocy(w["indeks"])
    (STRONA / "dane.json").write_text(json.dumps(dane, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- metodyka

def zbuduj_metodyke(w: dict, zrodla: list[dict], slownik) -> None:
    kat = slownik.kat
    poz = [v for v in kat.values() if v["waga"] > 0]
    wagi = "".join(f'<tr><td>{e(v["nazwa"])}</td><td class="num">{v["waga"]:+d}</td><td>{"tak" if v.get("wysoka") else "nie"}</td></tr>'
                   for v in sorted(kat.values(), key=lambda v: -v["waga"]))
    progi = "".join(f'<tr><td class="num">od {p["od"]}</td><td>{e(p.get("luzno", ""))}</td><td>{e(p["nazwa"])}</td><td>{e(p["opis"])}</td></tr>'
                    for p in slownik.progi)
    kryt = "".join(f"<li>{e(k[0])}</li>" for k in slownik.krytyczne_wz)
    n_akt = sum(z["status"] == "aktywne" for z in zrodla)
    jezyki = sorted({z.get("jezyk", "") for z in zrodla if z["status"] != "zablokowane"})
    tresc = f"""
<div class="wrap"><div class="obudowa"><div class="ekran">
{naglowek("metodyka", w["wygenerowano"])}

<section class="panel"><div class="proza">
  <h2>Metodyka w 2 minuty</h2>
  <p>Aplikacja codziennie czyta wiadomości z {len(zrodla)} sprawdzonych źródeł i szuka w nich zdarzeń, które w przeszłości poprzedzały wojnę. Nie zgaduje przyszłości. Liczy, ile wiarygodnych, niezależnych redakcji mówi naraz o tych samych niepokojących rzeczach wobec Polski i krajów bałtyckich.</p>
  <p>Wynik to <b>współczynnik wpierdolu (WW)</b> od 0 do 100. Im więcej różnych sygnałów naraz i im lepsze źródła, tym wyżej.</p>
</div></section>

<section class="panel" id="telefon"><div class="proza">
  <h3>Dla znajomych: ikona na telefonie i maile</h3>
  <p><b>Ikona na Androidzie.</b> Otwórz ten adres w Chrome, stuknij menu ⋮ w prawym górnym rogu i wybierz „Dodaj do ekranu głównego” albo „Zainstaluj aplikację”. Na pulpicie pojawi się zielony znak radiacji z podpisem „Ostrzeżenie”. Otwiera pulpit na pełnym ekranie, bez paska przeglądarki. Dane odświeżają się co godzinę.</p>
  <p><b>Ikona na iPhonie.</b> Otwórz adres w Safari, stuknij „Udostępnij” (kwadrat ze strzałką) i wybierz „Do ekranu początkowego”.</p>
  <p><b>Maile.</b> Na listę dopisuje osoba, która przysłała Ci link. Mail przychodzi tylko w tych sytuacjach:</p>
  <ul>
    <li><b>Raport tygodniowy</b> w poniedziałek ok. 7:00: poziom WW, co się działo w tygodniu. Przy okazji potwierdza, że system działa.</li>
    <li><b>Ostrzeżenie</b> albo <b>Alarm</b>: kilka kategorii sygnałów naraz z wielu niezależnych redakcji (opis w punkcie 3).</li>
    <li><b>Sygnał krytyczny</b>: jedno bardzo konkretne zdarzenie, np. ewakuacja ambasad albo mobilizacja, potwierdzone przez min. 2 wiarygodne redakcje. Mail od razu.</li>
    <li><b>Alarm trendu</b>: powolne narastanie zagrożenia przez kilka tygodni.</li>
  </ul>
  <p>Najwyżej 3 alarmy na dobę; kolejne przychodzą razem w jednym mailu. Poziom „Uwaga” i codzienne wahania nie wysyłają maili, widać je tylko na pulpicie. Cisza w skrzynce znaczy: nic ważnego się nie dzieje.</p>
</div></section>

<section class="panel" id="pomiar"><div class="proza">
  <h3>1. Jak mierzymy</h3>
  <ol>
    <li><b>Zbieramy wiadomości.</b> Co godzinę pobieramy kanały RSS: media publiczne, agencje, think tanki, rządy. Nagłówki po łotewsku, litewsku, estońsku, fińsku, szwedzku, norwesku, duńsku i rosyjsku tłumaczymy na polski.</li>
    <li><b>Szukamy sygnałów.</b> Każdą wiadomość sprawdzamy słownikiem {len(kat)} kategorii, np. „koncentracja wojsk przy granicy”, „ewakuacja dyplomatów”, „mobilizacja”. Słownik ma ok. {sum(len(v["wzorce"]) for v in kat.values())} wzorców w 3 językach.</li>
    <li><b>Ważymy.</b> Wiadomość liczy się mocniej, gdy pochodzi z lepszego źródła (ocena A–E) i dotyczy Polski, Bałtów, krajów nordyckich, Białorusi albo Kaliningradu. Wiadomość tylko o froncie w Ukrainie liczy się w 1/4.</li>
    <li><b>Nie dajemy się zakrzyczeć.</b> To samo wydarzenie opisane 20 razy liczy się jak jedno. Każda kategoria ma sufit: 4 mocne wiadomości to ok. 63% jej skali, więcej niewiele dodaje.</li>
    <li><b>Sumujemy.</b> WW to ważona suma kategorii. Wiadomości o rozejmie i rozmowach pokojowych obniżają wynik o maksymalnie 30%.</li>
  </ol>
  <div class="tab-prosta"><table><thead><tr><th>Kategoria</th><th>Waga</th><th>Liczy się do alarmu</th></tr></thead><tbody>{wagi}</tbody></table></div>
</div></section>

<section class="panel" id="poziomy"><div class="proza">
  <h3>2. Poziomy WW</h3>
  <div class="tab-prosta"><table><thead><tr><th>WW</th><th>Na luzie</th><th>Oficjalnie</th><th>Co to znaczy</th></tr></thead><tbody>{progi}</tbody></table></div>
  <p class="dim">Progi są tymczasowe. Tło 2025–2026 (drony, sabotaż, wojna w Ukrainie) jest stale podwyższone, więc skalibrujemy je po 30 dniach działania, 2 grudnia 2026.</p>
</div></section>

<section class="panel" id="alarmy"><div class="proza">
  <h3>3. Kiedy przychodzi alarm</h3>
  <p>Są 4 rodzaje alarmów. Mail dostaje lista odbiorców, najwyżej 3 alarmy na dobę (kolejne razem w jednym mailu). Niezależnie od alarmów w poniedziałek przychodzi raport tygodniowy.</p>
  <ul>
    <li><b>Spiętrzenie sygnałów.</b> Kategoria „świeci”, gdy pisze o niej min. 3 niezależne redakcje (ocena A–C) w 72 h, wobec Polski lub Bałtów. Redakcje jednego właściciela liczą się jako jedna. 1 kategoria: Uwaga (bez maila). 2 kategorie: Ostrzeżenie (mail). 3 kategorie, w tym ewakuacja, ostrzeżenia wywiadu, mobilizacja albo zamknięcia nieba: Alarm (mail pilny).</li>
    <li><b>Sygnał krytyczny.</b> Pojedyncze, bardzo konkretne zdarzenie, które samo jest powodem do alarmu, opisane przez min. 2 niezależne redakcje z oceną A lub B w 24 h. Mail od razu. Lista:<ul>{kryt}</ul></li>
    <li><b>Alarm trendu.</b> Łapie powolne narastanie, jak jesienią 2021. Codziennie sumujemy, o ile WW przekracza swoją normę z 30 dni sprzed tygodnia (metoda CUSUM). Mail, gdy suma z 14 dni przekroczy próg, a średnia z tygodnia jest min. 8 pkt nad normą. Działa po 21 dniach historii.</li>
    <li><b>Nagły skok kategorii.</b> Kategoria nagle 2 razy mocniejsza niż zwykle. Tylko wzmianka na pulpicie i w raporcie tygodniowym, bez osobnego maila.</li>
  </ul>
  <p>Ten sam sygnał krytyczny nie wraca w mailu przez 72 h, a alarm trendu przypomina się najwyżej raz w tygodniu.</p>
</div></section>

<section class="panel" id="zegar"><div class="proza">
  <h3>4. Zegar zagłady</h3>
  <p>To żart z poważnym przelicznikiem: WW 0 to 15 minut do północy, WW 100 to północ. Każdy punkt WW zabiera 9 sekund. Dziś WW {w["indeks"]:.0f}, czyli {sekundy_do_polnocy(w["indeks"]) // 60} min {sekundy_do_polnocy(w["indeks"]) % 60} s. Prawdziwy Zegar Zagłady prowadzi Bulletin of the Atomic Scientists i liczy go inaczej.</p>
</div></section>

<section class="panel" id="zrodla"><div class="proza">
  <h3>5. Skąd dane i jak oceniamy źródła</h3>
  <ul>
    <li><b>Rejestr źródeł:</b> {len(zrodla)} pozycji, {n_akt} aktywnych, języki: {e(", ".join(jezyki))}. Każde źródło ma ocenę według skali wywiadu NATO: A zawsze wiarygodne, B zwykle, C dość, D zwykle niewiarygodne, E niewiarygodne, F nie da się ocenić.</li>
    <li><b>Nowe źródło</b> przechodzi 30 dni próby: jest czytane i widoczne, ale nie liczy się do WW. Po próbie automat awansuje je albo blokuje według dwóch liczb: krzykliwości (ponad 15% sensacyjnych tytułów to blokada) i potwierdzalności (mniej niż 30% alarmów potwierdzonych przez inne redakcje to blokada).</li>
    <li><b>Martwe kanały</b> automat sprawdza w każdy poniedziałek, szuka nowego adresu w tej samej redakcji, a bez zastępstwa po 30 dniach blokuje.</li>
    <li><b>Kreml na podsłuchu.</b> Rosyjskie źródła państwowe (kremlin.ru, MSZ, TASS) czytamy tylko jako sygnał retoryki i budowania pretekstu. Nigdy nie potwierdzają faktów. RT i Sputnik są zablokowane.</li>
    <li><b>Ocen A–E automat nie zmienia sam.</b> To decyzja człowieka.</li>
  </ul>
</div></section>

<section class="panel" id="aktualizacja"><div class="proza">
  <h3>6. Jak często się aktualizuje</h3>
  <ul>
    <li><b>Co godzinę</b>: pobranie wiadomości, tłumaczenie, przeliczenie WW, kontrola alarmów. Gdy GitHub opuści przebieg, zapasowy uruchamia się po 30 minutach.</li>
    <li><b>W poniedziałek ok. 7:00</b>: raport tygodniowy mailem.</li>
    <li><b>W poniedziałek rano</b>: przegląd źródeł (martwe kanały, koniec prób) i sprawdzenie domen linków w VirusTotal (punkt 7).</li>
    <li><b>Strona</b>: obraz z ostatniego przeliczenia, godzina w prawym górnym rogu.</li>
  </ul>
</div></section>

<section class="panel" id="linki"><div class="proza">
  <h3>7. Bezpieczeństwo linków</h3>
  <p>Każdy link do artykułu, który widzisz na pulpicie albo w mailu, jest sprawdzany pod kątem bezpieczeństwa, zanim się pojawi. Kanał RSS może zostać przejęty albo podsunąć link do fałszywej strony, więc linkom nie ufamy z góry.</p>
  <ol>
    <li><b>Przy każdym przebiegu, co godzinę.</b> Link musi prowadzić do domeny tej samej redakcji, z której pochodzi wiadomość (wyjątki: inne domeny tego samego wydawcy, np. BBC, Sveriges Radio). Odrzucamy też adresy IP zamiast nazwy, domeny zapisane w punycode (podmienione litery, np. cyrylica udająca łacinę), adresy z wpisanym loginem, nietypowe porty i wszystko poza http i https. Podejrzany link zastępuje strona główna redakcji, a powód trafia do dziennika.</li>
    <li><b>Raz w tygodniu, w poniedziałek.</b> Wszystkie domeny źródeł i linków z ostatnich 7 dni sprawdzamy w <a href="https://www.virustotal.com/" target="_blank" rel="noopener">VirusTotal</a>, który zbiera oceny kilkudziesięciu programów antywirusowych. Pobieramy tylko gotowy raport o domenie, niczego nie wysyłamy do skanowania. Domena oznaczona jako groźna przez co najmniej 2 programy jest blokowana automatycznie; pojedyncze zgłoszenie sprawdza człowiek. Znane fałszywe alarmy (np. google.com) są na osobnej liście.</li>
  </ol>
  <p class="dim">Pierwsze sprawdzenie 3 listopada 2026: 52 domeny, żadna groźna. Kontrola zmniejsza ryzyko, ale go nie usuwa: strona prawdziwej redakcji też może zostać zhakowana. Nie podawaj haseł na stronach, do których prowadzą linki.</p>
</div></section>

<section class="panel" id="skan"><div class="proza">
  <h3>8. Zleć skan: sprawdzanie na Twoje polecenie</h3>
  <p>Usłyszałeś od kolegi, że „coś się dzieje na granicy”, albo przeczytałeś artykuł i chcesz wiedzieć, czy to prawda. W zakładce <a href="./#skan">ZLEĆ SKAN</a> to Ty wskazujesz, co sprawdzić, a aplikacja przeszukuje źródła na Twoje polecenie. Są dwie drogi.</p>
  <ol>
    <li><b>Szukaj teraz.</b> Bez konta i od razu: przeszukuje nagłówki z 3 dni ze wszystkich źródeł, także przetłumaczone z bałtyckich i nordyckich. Dopasowanie od początku słowa, więc „granica” znajdzie „granicy”, ale nie „nagranie”.</li>
    <li><b>Pełny skan albo weryfikacja linku.</b> Otwiera gotowe zgłoszenie na GitHubie (darmowe konto). W ok. 5 minut aplikacja (model Claude Sonnet): układa tezę i zapytania w 8 językach regionu, pobiera wszystkie kanały teraz, szuka w archiwum i w Google News z 30 dni, ocenia każde źródło (A–F albo „spoza rejestru”), ustala, kto działa i po co, rozważa co najmniej 3 wyjaśnienia i odpisuje werdyktem: potwierdzone, częściowo, niepotwierdzone, fałszywe albo za mało danych, z pewnością w procentach. Przy linku sprawdza też adres (jak w punkcie 7) i to, czy redakcja jest w rejestrze.</li>
  </ol>
  <p>Limity: 3 zgłoszenia na osobę i 10 razem na dobę, konto GitHub starsze niż 30 dni. Każde zgłoszenie to dokładnie 2 zapytania do modelu, który nie ma żadnych narzędzi, więc tekst podrzucony w zgłoszeniu albo na stronie z linku nie zmusi go do dodatkowej pracy. Zgłoszenie i odpowiedź są publiczne. Bez modelu językowego (awaria, budżet) odpowiedź zawiera tylko listę znalezionych wiadomości i liczbę niezależnych redakcji, bez werdyktu.</p>
</div></section>

<section class="panel" id="intencja"><div class="proza">
  <h3>9. Kto działa i po co: kontrola intencji</h3>
  <p>Słowa „wojsko przy granicy” nie mówią, czyje to wojsko. 3 listopada 2026 aplikacja policzyła „Polska wysyła wojsko na granicę z Rosją” jak koncentrację wojsk przeciwnika. Od wersji 2.0 działają dwie warstwy kontroli:</p>
  <ol>
    <li><b>Reguły, przy każdym przebiegu.</b> Pierwszy aktor w zdaniu i czasownik po nim. „Polska, urzędnicy, NATO + wysyła, szkoli, ćwiczy, buduje” to strona własna. Taki wpis nie liczy się do koncentracji wojsk, mobilizacji ani ćwiczeń przeciwnika; widać go w zakładce <a href="./#jakosc">JAKOŚĆ</a>.</li>
    <li><b>Model językowy, raz na godzinę.</b> Sprawdza tylko wiadomości, które mogą podnieść spiętrzenie sygnałów (72 h, Polska i sąsiedzi, źródło A–C). Przy pewności co najmniej 70% może zdjąć kategorię, ale nigdy jej nie dodaje i nie wycisza sygnałów krytycznych, bo jego pomyłka nie może uciszyć prawdziwego alarmu. Każdy wpis jest oceniany raz, wynik z powodem jest zapisany.</li>
  </ol>
</div></section>

<section class="panel" id="jakosc"><div class="proza">
  <h3>10. Kontrola jakości: sprawdzanie wstecz</h3>
  <p>Każde zgłoszenie trafia do historii z werdyktem, pewnością i prognozą: co powinno się pojawić w źródłach, jeśli teza jest prawdziwa. Po 7 i po 30 dniach aplikacja szuka jeszcze raz, tylko w wiadomościach opublikowanych po zgłoszeniu, i ocenia: teza okazała się prawdą, fałszem albo nadal nie wiadomo. Wynik dopisuje w wątku zgłoszenia.</p>
  <ul>
    <li><b>Trafność werdyktów:</b> odsetek rozstrzygniętych zgłoszeń, przy których werdykt wskazał dobry kierunek.</li>
    <li><b>Wynik Briera</b> (Brier 1950): kara za źle ustawioną pewność. 0 to ideał, 0,25 to poziom rzutu monetą. Pewność 90% przy tezie, która okazała się fałszem, kosztuje 0,81.</li>
    <li><b>Lekcje:</b> każda chybiona ocena daje jedno zdanie wniosku (np. „pomylona strona działania”). Lekcje czyta cotygodniowe autoulepszanie, które proponuje poprawki reguł do przeglądu przez właściciela.</li>
  </ul>
  <p class="dim">Historia zmian aplikacji i rejestr zgłoszeń zmian (Change Requests): <a href="https://github.com/Climbat1ze/wczesne-ostrzezenie/blob/main/CHANGELOG.md" target="_blank" rel="noopener">CHANGELOG.md</a> i <a href="https://github.com/Climbat1ze/wczesne-ostrzezenie/blob/main/docs/change_requests.md" target="_blank" rel="noopener">docs/change_requests.md</a>. Obecna wersja: {e(WERSJA)}.</p>
</div></section>

<section class="panel" id="ograniczenia"><div class="proza">
  <h3>11. Czego aplikacja nie umie</h3>
  <ul>
    <li>Myli się w obie strony, bo czyta słowa, nie sens. „Ulica Wojska Polskiego” to nie wojsko, a ironia to nie groźba.</li>
    <li>Nie zobaczy zagrożenia, którego nikt jeszcze nie opisał, ani nowego rodzaju zdarzeń spoza słownika.</li>
    <li>Nie przewiduje dat. Mówi tylko, ile sygnałów widać naraz.</li>
    <li>Nie jest komunikatem władz. Przy kolorze „Zatankuj do pełna” i „Do schronu” sprawdź <a href="https://www.gov.pl/web/rcb" target="_blank" rel="noopener">Rządowe Centrum Bezpieczeństwa</a> i Alert RCB w telefonie.</li>
  </ul>
</div></section>

<section class="panel" id="bledy"><div class="proza">
  <h3>12. Jak zgłosić błąd</h3>
  <ol>
    <li><b>Odpowiedz na dowolny mail z aplikacji.</b> Odpowiedź trafia do autora.</li>
    <li>Napisz jedno zdanie: która wiadomość albo który alarm, co jest źle i dlaczego. Przykład: „Ostrzeżenie z 2.11 fałszywe: »prowokacja« dotyczyła sporu o Trybunał, nie Rosji”.</li>
    <li>Chcesz dodać źródło: otwórz formularz <a href="https://github.com/Climbat1ze/wczesne-ostrzezenie/issues/new?template=nowe-zrodlo.yml" target="_blank" rel="noopener">nowe źródło</a> (konto GitHub). Bez konta albo żeby zakwestionować źródło: odpowiedz na mail, podaj nazwę, adres strony i powód.</li>
    <li>Masz pomysł na zmianę: otwórz <a href="https://github.com/Climbat1ze/wczesne-ostrzezenie/issues/new?template=change-request.yml" target="_blank" rel="noopener">zgłoszenie zmiany (Change Request)</a>.</li>
  </ol>
  <p>Zgłoszenia zbieramy do kalibracji słownika i progów. Pierwsza kalibracja: 2 grudnia 2026. Każda poprawka słownika działa wstecz na 90 dni zapisanych wiadomości.</p>
</div></section>

<section class="panel"><div class="proza">
  <h3>Źródła metody</h3>
  <ul>
    <li>Cynthia M. Grabo, <i>Anticipating Surprise: Analysis for Strategic Warning</i> (2002): listy wskaźników ostrzegawczych.</li>
    <li>NATO, skala oceny źródeł i informacji A–F, 1–6 (doktryna wywiadu sojuszu).</li>
    <li>E. S. Page, „Continuous Inspection Schemes”, <i>Biometrika</i> (1954): metoda CUSUM do wykrywania powolnych zmian.</li>
    <li>Richards J. Heuer Jr., <i>Psychology of Intelligence Analysis</i> (1999): analiza hipotez konkurencyjnych (ACH).</li>
    <li>Glenn W. Brier, „Verification of Forecasts Expressed in Terms of Probability”, <i>Monthly Weather Review</i> (1950): wynik Briera.</li>
  </ul>
</div></section>

{stopka(len(zrodla))}
</div></div></div>
"""
    glowa, cialo = dokument("Wczesne Ostrzeżenie: Metodyka", tresc)
    zapisz_pelny("metodyka.html", glowa, cialo)


# ---------------------------------------------------------------- wersja 2.0: skan, zgłoszenia, jakość

CSS_V2 = """
/* skan na żądanie, zgłoszenia, jakość (wersja 2.0) */
.skan-form { display: grid; gap: 8px; }
.skan-form input, .skan-form textarea { font: inherit; font-size: .95rem; padding: 6px 8px; border: 1px solid var(--ph-dim); border-radius: 0;
  background: var(--screen); color: var(--ph); width: 100%; min-width: 0; }
.skan-form textarea { min-height: 3.2em; resize: vertical; }
.przyciski { display: flex; flex-wrap: wrap; gap: 8px; }
.przycisk { font: inherit; font-size: .85rem; letter-spacing: .08em; text-transform: uppercase; padding: 6px 12px; cursor: pointer;
  border: 1px solid var(--ph); background: transparent; color: var(--ph); text-decoration: none; display: inline-block; }
.przycisk.pelny { background: var(--ph); color: var(--ink-inv); text-shadow: none; }
.przycisk:focus-visible, .skan-form input:focus-visible, .skan-form textarea:focus-visible { outline: 2px solid var(--ph); outline-offset: 2px; }
.dwie { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
.wynik-szukaj { font-size: .84rem; }
.wynik-szukaj li { padding: 6px 0; border-bottom: 1px dashed var(--ph-faint); list-style: none; }
.wynik-szukaj ul { padding: 0; margin: 0; }
.werdykt { display: inline-block; border: 1px solid var(--ph-dim); padding: 0 6px; font-size: .75rem; white-space: nowrap; }
.werdykt.w-potwierdzone, .werdykt.w-czesciowo { background: var(--ph); color: var(--ink-inv); text-shadow: none; }
.werdykt.w-falszywe { text-decoration: line-through; }
"""

JS_V2 = r"""
(function () {
  var P = document.getElementById('pulpit'); var REPO = (P && P.dataset.repo) || 'Climbat1ze/wczesne-ostrzezenie';
  function issue(pola) {
    var q = Object.keys(pola).filter(function (k) { return pola[k]; })
      .map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(pola[k]); }).join('&');
    return 'https://github.com/' + REPO + '/issues/new?template=skan.yml&' + q;
  }
  var qs = document.getElementById('s-slowa'), qk = document.getElementById('s-kontekst'), qw = document.getElementById('s-wynik');
  var ql = document.getElementById('l-link'), qlk = document.getElementById('l-kontekst');
  if (!qs) return;
  function rdzen(s) { return s.length <= 5 ? s : s.slice(0, Math.max(5, s.length - 2)); }
  var dane = null;
  function zaladuj(cb) {
    if (dane) return cb(dane);
    var u = /github\.io$/.test(location.hostname) || location.protocol === 'file:' || location.hostname === 'localhost' ? 'szukaj.json'
      : 'https://climbat1ze.github.io/wczesne-ostrzezenie/szukaj.json';
    qw.textContent = 'Wczytuję nagłówki z 3 dni...';
    fetch(u).then(function (r) { return r.json(); }).then(function (d) { dane = d; cb(d); })
      .catch(function () { qw.textContent = 'Nie udało się wczytać nagłówków. Użyj pełnego skanu przez GitHub.'; });
  }
  function el(tag, txt, attrs) { var x = document.createElement(tag); if (txt) x.textContent = txt; for (var a in (attrs || {})) x.setAttribute(a, attrs[a]); return x; }
  function szukaj() {
    var slowa = (qs.value || '').toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) || [];
    if (!slowa.length) { qw.textContent = 'Wpisz co najmniej jedno słowo (3 litery i więcej).'; return; }
    var r = slowa.map(rdzen);
    zaladuj(function (d) {
      var re = r.map(function (k) { return new RegExp('(^|[^\\p{L}\\p{N}])' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'u'); });
      var traf = d.n.filter(function (x) { var t = (x.t + ' ' + (x.o || '')).toLowerCase(); return re.every(function (k) { return k.test(t); }); });
      qw.innerHTML = '';
      var naglowek = el('p', traf.length + ' wiadomości z 3 dni zawiera wszystkie słowa (' + d.n.length + ' sprawdzonych, ' + d.zrodel + ' źródeł). '
        + (traf.length ? 'Pokazuję do 30 najnowszych.' : 'Spróbuj innych słów albo zleć pełny skan: obejmie też Google News i 30 dni.'));
      naglowek.className = 'dim'; qw.appendChild(naglowek);
      var ul = el('ul');
      traf.slice(0, 30).forEach(function (x) {
        var li = el('li'), a = el('a', x.t, { href: x.l, target: '_blank', rel: 'noopener' });
        li.appendChild(a);
        li.appendChild(el('div', x.z + ' · ocena ' + x.c + ' · ' + x.d.replace('T', ' '), { 'class': 'dim' }));
        ul.appendChild(li);
      });
      qw.appendChild(ul);
    });
  }
  document.getElementById('s-szukaj').addEventListener('click', szukaj);
  qs.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); szukaj(); } });
  document.getElementById('s-zlec').addEventListener('click', function () {
    if (!qs.value.trim()) { qw.textContent = 'Wpisz słowa kluczowe.'; return; }
    window.open(issue({ title: '[skan] ' + qs.value.trim().slice(0, 80), slowa: qs.value.trim(), kontekst: qk.value.trim() }), '_blank', 'noopener');
  });
  document.getElementById('l-zlec').addEventListener('click', function () {
    var v = (ql.value || '').trim();
    if (!/^https?:\/\//i.test(v)) { document.getElementById('l-info').textContent = 'Wklej pełny link zaczynający się od https://'; return; }
    window.open(issue({ title: '[link] ' + v.replace(/^https?:\/\//, '').slice(0, 80), link: v, kontekst: qlk.value.trim() }), '_blank', 'noopener');
  });
})();
"""


def zapisz_szukaj(zrodla: list[dict], dni: int = 3) -> int:
    """strona/szukaj.json: nagłówki z 3 dni do szybkiego szukania w przeglądarce (bez konta, bez modelu)."""
    import ostrzezenie as o  # noqa: E402
    ocena = {z["id"]: z["wiarygodnosc"] if z.get("grupa") != "@wydawca" else "?" for z in zrodla}
    granica = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=dni)).isoformat()
    lista = sorted((w for w in o.czytaj_naglowki() if w.get("data", "") >= granica), key=lambda w: w["data"], reverse=True)
    n = [{"t": w["tytul"][:200], **({"o": w["oryginal"][:200]} if w.get("oryginal") else {}), "z": w.get("wydawca", "")[:50],
          "c": ocena.get(w.get("zrodlo"), "?"), "d": w["data"][:16], "l": w.get("link", "")} for w in lista]
    (STRONA / "szukaj.json").write_text(json.dumps({"wygenerowano": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                                                   "zrodel": len({w.get("zrodlo") for w in lista}), "n": n},
                                                  ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(n)


def _werdykt_html(kod: str | None) -> str:
    import zgloszenia as zg  # noqa: E402
    if not kod:
        return '<span class="dim">–</span>'
    return f'<span class="werdykt w-{e(kod)}">{e(zg.WERDYKTY.get(kod, kod))}</span>'


def sekcje_v2(w: dict, repo: str) -> str:
    import zgloszenia as zg  # noqa: E402
    import jakosc as jk  # noqa: E402
    hist = list(reversed(zg.historia()))[:20]
    wiersze = []
    for r in hist:
        a = r.get("analiza", {})
        co = r.get("slowa") or r.get("domena") or r.get("link", "")[:60]
        ident = (f'<a href="https://github.com/{e(repo)}/issues/{int(r["issue"])}" target="_blank" rel="noopener">{e(r["id"])}</a>'
                 if r.get("issue") else e(r["id"]))
        ret = []
        for etap in ("7d", "30d"):
            x = (r.get("retro") or {}).get(etap)
            if x:
                znak = {True: "trafny", False: "chybiony"}.get(x.get("werdykt_trafny"), zg.WYNIK_RETRO.get(x.get("wynik"), "?"))
                ret.append(f"{etap.replace('d', ' dni')}: {znak}")
        wiersze.append(f'<tr><td class="num">{ident}</td><td class="num">{e(data_pl(r["ts"]))}</td>'
                       f'<td>{"LINK " if r.get("tryb") == "link" else ""}{e(co)}<div class="notatka">{e(a.get("teza", "")[:160])}</div></td>'
                       f'<td>{_werdykt_html(a.get("werdykt"))}</td><td class="num">{"–" if a.get("pewnosc") is None else f"{a["pewnosc"] * 100:.0f}%"}</td>'
                       f'<td>{e("; ".join(ret) or "czeka")}</td></tr>')
    tabela_zg = ("".join(wiersze) or '<tr><td colspan="6" class="dim">Brak zgłoszeń. Pierwsze zgłoszenie zleć w zakładce ZLEĆ SKAN.</td></tr>')
    p = zg.podsumowanie()
    ocena = None
    try:
        lj = [json.loads(l) for l in (jk.DANE / "jakosc.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        ocena = lj[-1] if lj else None
    except FileNotFoundError:
        pass
    it = w.get("intencja") or {}
    wl = w.get("wlasne") or []
    lista_wl = "".join(
        f'<li><div><a href="{e(x["link"])}" target="_blank" rel="noopener">{e(x["tytul"])}</a></div>'
        f'<div class="meta"><span>{e(x["wydawca"])}</span><span class="num">{data_pl(x["data"])}</span>'
        f'<span>nie liczy się do: {e(", ".join(x.get("zdjete_nazwy") or x["zdjete"]))}</span></div><div class="dim" style="font-size:.78rem">{e(x["powod"])}</div></li>'
        for x in wl) or '<li class="dim">Brak w 72 h.</li>'
    kafle = (
        f'<div class="kafel"><span class="etykieta">Trafność werdyktów (wstecz)</span>'
        f'<span class="w num">{"–" if p["trafnosc"] is None else f"{p["trafnosc"] * 100:.0f}%"}</span>'
        f'<span class="dim" style="font-size:.78rem">{p["trafne"]} z {p["rozstrzygniete"]} rozstrzygniętych; czeka {p["czeka_na_retro"]}</span></div>'
        f'<div class="kafel"><span class="etykieta">Kalibracja pewności (Brier)</span>'
        f'<span class="w num">{"–" if p["brier"] is None else f"{p["brier"]:.2f}"}</span>'
        f'<span class="dim" style="font-size:.78rem">0 = idealnie, 0,25 = rzut monetą</span></div>'
        f'<div class="kafel"><span class="etykieta">Klasyfikacja nagłówków</span>'
        f'<span class="w num">{"–" if not ocena else f"{ocena["odsetek"] * 100:.0f}%"}</span>'
        f'<span class="dim" style="font-size:.78rem">{"brak oceny" if not ocena else f"trafnych w losowej próbce {ocena["ocenione"]}, {ocena["ts"][:10]}"}</span></div>'
        f'<div class="kafel"><span class="etykieta">Kontrola intencji (7 dni)</span>'
        f'<span class="w num">{it.get("ocenione", 0)}</span>'
        f'<span class="dim" style="font-size:.78rem">wpisów sprawdził model; strona własna lub sojusznicza: '
        f'{(it.get("po_stronie") or {}).get("wlasna", 0) + (it.get("po_stronie") or {}).get("sojusznicza", 0)}</span></div>')
    return f"""
<section id="skan" class="panel">
  <div class="tytul"><h3>Zleć skan</h3><span class="etykieta">ty wskazujesz, aplikacja sprawdza</span></div>
  <p style="margin-top:0">Usłyszałeś coś albo przeczytałeś? Wpisz słowa lub wklej link, a aplikacja przeszuka swoje źródła na Twoje zlecenie.</p>
  <div class="dwie">
    <div class="skan-form">
      <label class="etykieta" for="s-slowa">Słowa kluczowe</label>
      <input id="s-slowa" type="search" placeholder="np. wojsko granica Białoruś" autocomplete="off">
      <label class="etykieta" for="s-kontekst">Co usłyszałeś (opcjonalnie, do pełnego skanu)</label>
      <textarea id="s-kontekst" placeholder="np. kolega mówi, że urzędnicy szkolą się z broni palnej"></textarea>
      <div class="przyciski"><button class="przycisk pelny" id="s-szukaj" type="button">Szukaj teraz (3 dni)</button>
        <button class="przycisk" id="s-zlec" type="button">Zleć pełny skan z oceną</button></div>
    </div>
    <div class="skan-form">
      <label class="etykieta" for="l-link">Link do sprawdzenia</label>
      <input id="l-link" type="url" placeholder="https://..." autocomplete="off">
      <label class="etykieta" for="l-kontekst">Co chcesz wiedzieć (opcjonalnie)</label>
      <textarea id="l-kontekst" placeholder="np. czy to prawda i czy piszą o tym inni"></textarea>
      <div class="przyciski"><button class="przycisk" id="l-zlec" type="button">Zleć weryfikację linku</button></div>
      <p class="dim" id="l-info" style="font-size:.8rem"></p>
    </div>
  </div>
  <p class="dim" style="font-size:.8rem">„Szukaj teraz” działa od razu i bez konta: przeszukuje nagłówki z 3 dni ze wszystkich źródeł. Pełny skan i weryfikacja linku otwierają gotowe zgłoszenie na GitHubie (potrzebne darmowe konto): aplikacja pobiera wszystkie kanały, szuka w Google News z 30 dni, ocenia źródła, sprawdza kto działa i z jaką intencją, i w ok. 5 minut odpisuje w zgłoszeniu werdyktem z pewnością. Limit: 3 zgłoszenia na osobę na dobę, konto GitHub starsze niż 30 dni. Szczegóły w <a href="metodyka.html#skan">metodyce</a>.</p>
  <div class="wynik-szukaj" id="s-wynik" aria-live="polite"></div>
</section>

<section id="zgloszenia" class="panel">
  <div class="tytul"><h3>Historia zgłoszeń</h3><span class="etykieta">{p["zgloszen"]} w 90 dniach · sprawdzane wstecz po 7 i 30 dniach</span></div>
  <div class="tabela"><table><thead><tr><th>Nr</th><th>Kiedy</th><th>Co sprawdzano</th><th>Werdykt</th><th>Pewność</th><th>Wstecz</th></tr></thead>
  <tbody>{tabela_zg}</tbody></table></div>
</section>

<section id="jakosc" class="panel">
  <div class="tytul"><h3>Kontrola jakości</h3><span class="etykieta">czy aplikacja się myli i jak bardzo</span></div>
  <div class="kafle">{kafle}</div>
  <div><div class="etykieta" style="margin:10px 0 6px">Zdjęte przez kontrolę strony i intencji, 72 h (nie podnoszą WW)</div>
  <p class="dim" style="font-size:.8rem">Głównie wiadomości, w których działa Polska, Bałtowie, kraje nordyckie albo NATO: wysyłają wojsko, ćwiczą, szkolą się. To reakcja obronna, nie wskaźnik ataku przeciwnika. Tu trafiają też wpisy, które model uznał za niezwiązane z zagrożeniem (z pewnością co najmniej 70%). Pod każdym powód.</p>
  <ul class="lista">{lista_wl}</ul></div>
</section>
"""
