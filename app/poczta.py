"""Wysyłka maili: skrót dnia i alarm spiętrzenia sygnałów.

Konfiguracja wyłącznie przez zmienne środowiskowe (w GitHub Actions: sekrety), żeby adresy
i hasło nigdy nie trafiły do repo:
  SMTP_USER   konto nadawcy, np. adres Gmail
  SMTP_PASS   hasło aplikacji Gmail (nie zwykłe hasło; wymaga weryfikacji dwuetapowej)
  MAIL_DO     odbiorcy, rozdzieleni przecinkami
  SMTP_HOST   domyślnie smtp.gmail.com
  SMTP_PORT   domyślnie 465 (SSL)
  SITE_URL    opcjonalnie adres strony, dodawany do maila
"""
from __future__ import annotations

import datetime as dt
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from html import escape as e
from zoneinfo import ZoneInfo

WAW = ZoneInfo("Europe/Warsaw")
MIESIACE = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
            "września", "października", "listopada", "grudnia"]
KOLORY = {"zielony": "#23794a", "zolty": "#9a6f00", "pomaranczowy": "#bf5316", "czerwony": "#b0241c"}
KOLOR_ALARMU = ["#566573", "#9a6f00", "#bf5316", "#b0241c"]


def _data(iso: str) -> str:
    d = dt.datetime.fromisoformat(iso).astimezone(WAW)
    return f"{d.day} {MIESIACE[d.month - 1]}, {d:%H:%M}"


def _zmiana(teraz, ref) -> str:
    if ref is None:
        return "brak porównania"
    d = teraz - ref
    return "bez zmian" if abs(d) < 3 else f"{'wzrost' if d > 0 else 'spadek'} {d:+.0f}"


def zbuduj(w: dict, slownik, rodzaj: str = "skrot") -> tuple[str, str, str]:
    """Zwraca (temat, tekst, html). rodzaj: 'skrot' albo 'alarm'."""
    prog, zb, t = w["prog"], w["zbieznosc"], w["trend"]
    d = dt.date.fromisoformat(w["dzien"])
    kiedy = f"{d.day} {MIESIACE[d.month - 1]}"
    if rodzaj == "alarm":
        temat = f"{zb['nazwa'].upper()}: spiętrzenie sygnałów wobec Polski i Bałtów ({kiedy})"
    else:
        temat = (f"Skrót {kiedy}: {prog.get('luzno', prog['nazwa']).lower()}, WW {w['indeks']:.0f}"
                 f" ({_zmiana(w['indeks'], t['sr_7'])} wobec tygodnia)")
    url = os.environ.get("SITE_URL", "")
    news = w["najwazniejsze"][:8]

    tekst = [temat, "", *[f"- {s}" for s in w["skrot"]], "", "Najważniejsze wiadomości (24 h):"]
    for n in news:
        tekst.append(f"- {n['tytul']} ({', '.join(z for z, _ in n['zrodla'][:3])})\n  {n['link']}")
    if url:
        tekst += ["", f"Pełny obraz i źródła: {url}"]
    if url:
        tekst += [f"Jak to działa: {url.rstrip('/')}/metodyka.html"]
    tekst += ["", "Błąd albo fałszywy alarm? Odpowiedz na ten mail jednym zdaniem: co jest źle i dlaczego.",
              "Prywatne narzędzie, nie komunikat władz. Oficjalne alerty: RCB (gov.pl/web/rcb)."]

    html = _skrot_html(w, slownik, temat, news, url, rodzaj)
    return temat, "\n".join(tekst), html


# ---------------------------------------------------------------- wygląd retro-terminala (inline, bo Gmail nie czyta <style> ani SVG)

_OBRAZY: dict[str, bytes] = {}  # obrazki do wklejenia w treść maila (cid:nazwa)
T = {"bg": "#030a05", "ekran": "#071a0e", "ph": "#4dff91", "ph2": "#33d673", "dim": "#1d8a4b", "faint": "#0f3d22", "inv": "#021007"}
FONT = "'Courier New', Courier, ui-monospace, monospace"


def _ramka(srodek: str, naglowek: str = "WCZESNE OSTRZEŻENIE · TERMINAL OBRONY CYWILNEJ") -> str:
    return (f'<!doctype html><html lang="pl"><body style="margin:0;background:{T["bg"]}">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{T["bg"]}"><tr><td align="center" style="padding:18px 10px">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;background:{T["ekran"]};border:2px solid {T["dim"]};'
            f'border-radius:10px;font-family:{FONT};color:{T["ph"]};font-size:14px;line-height:1.55">'
            f'<tr><td style="padding:14px 18px 8px;border-bottom:1px dashed {T["faint"]}">'
            f'<span style="font-size:22px;vertical-align:middle">&#9762;</span> '
            f'<span style="font-size:13px;letter-spacing:2px;color:{T["ph2"]};vertical-align:middle">{e(naglowek)}</span></td></tr>'
            f'{srodek}'
            f'<tr><td style="padding:12px 18px 16px;font-size:12px;color:{T["ph2"]};border-top:1px dashed {T["faint"]}">'
            f'&gt; BŁĄD ALBO FAŁSZYWY ALARM? Odpowiedz na ten mail jednym zdaniem: co jest źle i dlaczego.'
            f'{_link_metodyki()}<br>&gt; Prywatne narzędzie znajomych, nie komunikat władz. Oficjalne alerty: RCB (gov.pl/web/rcb) i Alert RCB w telefonie.</td></tr>'
            f'</table></td></tr></table></body></html>')


METODYKA_SKROT = [
    ("Co to jest WW", "Współczynnik wpierdolu 0–100. Co godzinę czytamy kanały RSS z ocenionych źródeł (media publiczne, agencje, "
                      "think tanki, rządy; bałtyckie nagłówki tłumaczymy) i szukamy {kat} rodzajów sygnałów, które w przeszłości "
                      "poprzedzały wojnę: koncentracja wojsk, ewakuacja dyplomatów, mobilizacja, sabotaż i inne."),
    ("Jak liczymy", "Wiadomość waży więcej, gdy pochodzi z lepszego źródła i dotyczy Polski lub Bałtów. To samo wydarzenie opisane "
                    "20 razy liczy się raz. Rozmowy pokojowe obniżają wynik."),
    ("Poziomy", "{poziomy}. Progi skalibrujemy po 30 dniach (2 grudnia)."),
    ("Alarmy", "Mail przychodzi osobno, gdy: 2 kategorie sygnałów naraz potwierdzi po 3 niezależne redakcje w 72 h; "
               "2 wiarygodne redakcje opiszą sygnał krytyczny (ewakuacja ambasady, mobilizacja, art. 4/5 NATO, zamknięcie nieba, atak); "
               "albo WW rośnie powoli przez ponad tydzień (alarm trendu)."),
    ("Zegar zagłady", "WW 0 to 15 minut do północy, WW 100 to północ. Żart z poważnym przelicznikiem."),
    ("Rytm", "Odczyt co godzinę, skrót mailem codziennie ok. 6:47, przegląd źródeł w poniedziałki."),
    ("Czego nie umie", "Czyta słowa, nie sens, więc myli się w obie strony. Nie przewiduje dat. Nie jest komunikatem władz."),
]


def _metodyka_skrot(slownik) -> str:
    poziomy = ", ".join(f"od {p['od']} {p.get('luzno', p['nazwa'])}" for p in slownik.progi)
    linie = "".join(
        f'<div style="margin-bottom:6px"><span style="color:{T["ph"]};font-weight:bold">{e(t.upper())}:</span> '
        f'<span style="color:{T["ph2"]}">{e(o.format(kat=len(slownik.kat), poziomy=poziomy))}</span></div>' for t, o in METODYKA_SKROT)
    return _zakladka("METODYKA W 1 MINUTĘ") + f'<div style="font-size:12px;line-height:1.5">{linie}</div>'


def _link_metodyki() -> str:
    url = os.environ.get("SITE_URL", "")
    return f' <a href="{e(url.rstrip("/"))}/metodyka.html" style="color:{T["ph"]}">Jak to działa</a>.' if url else ""


def _miernik(indeks: float, komorek: int = 24) -> str:
    pelne = round(max(0, min(100, indeks)) / 100 * komorek)
    return "█" * pelne + "░" * (komorek - pelne)


def _wiersz(tresc: str, styl: str = "") -> str:
    return f'<tr><td style="padding:10px 18px;{styl}">{tresc}</td></tr>'


def _zakladka(nazwa: str) -> str:
    """Nagłówek sekcji w stylu zakładki terminala (linki wewnątrz maila Gmail i tak ucina)."""
    return (f'<div style="margin-bottom:8px;border-bottom:2px solid {T["dim"]}"><span style="display:inline-block;background:{T["faint"]};'
            f'border:2px solid {T["dim"]};border-bottom:0;padding:2px 10px;font-size:13px;letter-spacing:2px;font-weight:bold">{e(nazwa)}</span></div>')


def _sygnaly_html(w: dict, slownik) -> str:
    zb = w["zbieznosc"]
    wiersze = []
    for k, v in sorted(slownik.kat.items(), key=lambda kv: (kv[1]["waga"] <= 0, -kv[1]["waga"], kv[1]["nazwa"])):
        n = w["natezenie"].get(k, 0)
        g = zb["kategorie"].get(k, {}).get("grupy")
        swieci = g is not None and g >= 3
        prawa = ("obniża WW" if v["waga"] < 0 else "tło") if g is None else f"{g} red./72 h"
        styl_prawa = f'background:{T["ph"]};color:{T["inv"]};padding:0 4px' if swieci else f'color:{T["ph2"]}'
        wiersze.append(
            f'<tr><td style="padding:3px 6px 3px 0;font-size:12px;width:46%">{e(v["nazwa"])}</td>'
            f'<td style="padding:3px 6px;font-size:12px;white-space:nowrap;color:{T["ph"] if v["waga"] > 0 else T["dim"]}">{_miernik(n * 100, 12)}</td>'
            f'<td style="padding:3px 0;font-size:11px;text-align:right;white-space:nowrap"><span style="{styl_prawa}">{e(prawa)}</span></td></tr>')
    return (_zakladka("SYGNAŁY")
            + f'<div style="font-size:11px;color:{T["ph2"]};margin-bottom:6px">Pasek: natężenie w 24 h. Prawa kolumna: niezależne redakcje A–C w 72 h; od 3 kategoria się świeci.</div>'
            + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(wiersze)}</table>')


def _analogia_html(w: dict) -> str:
    wiersze = "".join(
        f'<tr><td valign="top" style="padding:3px 8px 3px 0;width:26px"><span style="display:inline-block;width:18px;text-align:center;'
        f'{"background:" + T["ph"] + ";color:" + T["inv"] if a["trafienie"] else "border:1px solid " + T["dim"]}">{"!" if a["trafienie"] else "·"}</span></td>'
        f'<td valign="top" style="padding:3px 8px 3px 0;font-size:11px;color:{T["ph2"]};white-space:nowrap">{e(a["kiedy"])}</td>'
        f'<td style="padding:3px 0;font-size:12px">{e(a["co"])}</td></tr>' for a in w["analogia"])
    traf = sum(a["trafienie"] for a in w["analogia"])
    return (_zakladka(f"ANALOGIA 2021/22 · {traf} Z {len(w['analogia'])}")
            + f'<div style="font-size:11px;color:{T["ph2"]};margin-bottom:6px">Zdarzenia sprzed 24.02.2022. „!”: w 30 dniach min. 2 niezależne redakcje opisały podobny sygnał wobec Polski lub Bałtów.</div>'
            + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{wiersze}</table>')


def _zrodla_html(w: dict) -> str:
    pob = w.get("pobranie") or {}
    jak = w.get("jakosc") or {}
    awarie = sum(1 for j in jak.values() if j.get("ostatni_blad"))
    zm = (w.get("utrzymanie") or {}).get("zmiany", [])
    linie = [f"Kanały działające w tym odczycie: {pob.get('ok', '–')} z {pob.get('razem', '–')}.",
             f"Kanały z błędem: {awarie}.",
             "Zmiany źródeł w tym przebiegu: " + ("; ".join(f"{z['nazwa']} {z['z']} → {z['na']}" for z in zm) if zm else "brak") + "."]
    return _zakladka("ŹRÓDŁA") + "".join(f'<div style="font-size:12px;color:{T["ph2"]}">&gt; {e(l)}</div>' for l in linie)


def _skrot_html(w: dict, slownik, temat: str, news: list, url: str, rodzaj: str) -> str:
    prog, zb, t = w["prog"], w["zbieznosc"], w["trend"]
    s = round(900 * (1 - max(0.0, min(100.0, w["indeks"])) / 100))
    alarm_zb = zb["poziom"] >= 2
    nazwa = e(prog.get("luzno", prog["nazwa"]).upper())
    poziom_styl = f'background:{T["ph"]};color:{T["inv"]};padding:0 6px;' if prog["kolor"] == "czerwony" else ""
    obrazek = ""
    try:
        import obraz  # noqa: E402
        _OBRAZY["licznik"] = obraz.licznik_png(w["indeks"], slownik.progi, s, prog.get("luzno", prog["nazwa"]))
        obrazek = (f'<img src="cid:licznik" width="600" style="width:100%;max-width:600px;height:auto;display:block;margin:6px auto 4px;border:0" '
                   f'alt="Współczynnik wpierdolu {w["indeks"]:.0f}/100, {e(prog.get("luzno", prog["nazwa"]))}, {s // 60} min do północy">')
    except Exception as ex:  # noqa: BLE001  — bez obrazka mail i tak wychodzi, z paskiem tekstowym
        print("Obrazek licznika: pominięty,", ex)
    licznik = (obrazek + f'<div style="color:{T["ph2"]}">{e(prog.get("luzno_opis", prog["opis"]))}</div>') if obrazek else (
        f'<div style="font-size:12px;letter-spacing:2px;color:{T["ph2"]}">WSPÓŁCZYNNIK WPIERDOLU · AKA FUCK-O-METER</div>'
        f'<div style="font-size:44px;line-height:1.1;font-weight:bold">{w["indeks"]:.0f}<span style="font-size:18px;color:{T["ph2"]}">/100</span></div>'
        f'<div style="font-size:14px;white-space:nowrap;overflow:hidden">[{_miernik(w["indeks"])}]</div>'
        f'<div style="font-size:11px;color:{T["dim"]};letter-spacing:1px">0 PIJ KAWĘ · 30 SPRAWDŹ PLECAK · 50 ZATANKUJ · 70 DO SCHRONU</div>'
        f'<div style="font-size:26px;font-weight:bold;margin-top:8px"><span style="{poziom_styl}">{nazwa}</span></div>'
        f'<div style="color:{T["ph2"]}">{e(prog.get("luzno_opis", prog["opis"]))}</div>')
    kafle = "".join(
        f'<td width="25%" valign="top" style="border:1px solid {T["ph"] if on else T["faint"]};background:{T["faint"] if on else T["ekran"]};padding:6px 8px">'
        f'<div style="font-size:10px;letter-spacing:1px;color:{T["ph2"]}">{e(et)}</div><div style="font-size:15px;font-weight:bold">{e(wart)}</div></td>'
        for et, wart, on in [
            ("WOBEC 30 DNI", _zmiana(w["indeks"], t["sr_30"]).upper(), (w["indeks"] - (t["sr_30"] or w["indeks"])) >= 3),
            ("SPIĘTRZENIE", zb["nazwa"].upper(), alarm_zb),
            ("WOBEC 7 DNI", _zmiana(w["indeks"], t["sr_7"]).upper(), (w["indeks"] - (t["sr_7"] or w["indeks"])) >= 3),
            ("ANALOGIA 2021/22", f'{sum(a["trafienie"] for a in w["analogia"])} / {len(w["analogia"])}', False)])
    skrot = "".join(f'<div style="margin-bottom:4px"><span style="color:{T["ph2"]}">&gt;</span> {e(x)}</div>' for x in w["skrot"])
    wiad = "".join(
        f'<div style="padding:8px 0;border-top:1px dashed {T["faint"]}">'
        f'<a href="{e(n["link"])}" style="color:{T["ph"]};font-weight:bold">{e(n["tytul"])}</a>'
        + (f' <span style="font-size:11px;color:{T["ph2"]}">[TŁUM. Z {e(n["jezyk"].upper())}]</span>' if n.get("jezyk") else "")
        + f'<div style="font-size:12px;color:{T["ph2"]}">{e(", ".join(z for z, _ in n["zrodla"][:3]))} · {e(_data(n["data"]))} · '
        f'{e(", ".join(slownik.kat[k]["nazwa"].lower() for k in n["kategorie"]))}</div></div>'
        for n in news) or f'<div style="color:{T["ph2"]}">Cisza w eterze: brak wiadomości o Polsce i Bałtach z trafieniem wskaźników w 24 h.</div>'
    naglowek_alarmu = (_wiersz(f'<div style="background:{T["ph"]};color:{T["inv"]};padding:6px 10px;font-weight:bold;font-size:16px">'
                               f'&#9888; {e(temat.upper())}</div>') if rodzaj == "alarm" else "")
    srodek = (naglowek_alarmu
              + _wiersz(f'<div style="font-size:11px;color:{T["ph2"]}">OSTATNI ODCZYT: {e(_data(w["wygenerowano"]))}</div>{licznik}', "text-align:center")
              + _wiersz(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="4"><tr>{kafle}</tr></table>', "padding-top:0")
              + _wiersz(_zakladka("SKRÓT DNIA") + skrot)
              + _wiersz(_sygnaly_html(w, slownik))
              + _wiersz(_zakladka("WIADOMOŚCI · 24 H") + wiad)
              + _wiersz(_analogia_html(w))
              + _wiersz(_zrodla_html(w))
              + (_wiersz(f'<a href="{e(url)}" style="color:{T["ph"]}">&gt; OTWÓRZ PULPIT: wykres, sygnały, źródła</a>') if url else "")
              + _wiersz(_metodyka_skrot(slownik)))
    return _ramka(srodek)


def zbuduj_tydzien(w: dict, slownik) -> tuple[str, str, str]:
    """Tygodniowy mail kontrolny: system działa, gdzie jest WW, co było w tygodniu, link do strony."""
    prog, zb, t = w["prog"], w["zbieznosc"], w["trend"]
    d = dt.date.fromisoformat(w["dzien"])
    url = os.environ.get("SITE_URL", "")
    hist = [h for h in w["historia"] if not h.get("rek")][-7:] or [{"indeks": w["indeks"], "alarm": zb["poziom"]}]
    wart = [h["indeks"] for h in hist]
    dni_alarm = sum(1 for h in hist if h["alarm"] >= 2)
    temat = f"Tydzień do {d.day} {MIESIACE[d.month - 1]}: WW {w['indeks']:.0f}, {prog.get('luzno', prog['nazwa']).lower()}. System działa."
    linie = [f"Współczynnik wpierdolu teraz: {w['indeks']:.0f}/100 ({prog.get('luzno', prog['nazwa'])}).",
             f"Ostatnie {len(wart)} dni: średnio {sum(wart) / len(wart):.0f}, najniżej {min(wart):.0f}, najwyżej {max(wart):.0f}; wobec 30 dni: {_zmiana(w['indeks'], t['sr_30'])}.",
             f"Dni z ostrzeżeniem lub alarmem spiętrzenia: {dni_alarm}. Dziś: {zb['nazwa'].lower()}.",
             f"Alarm trendu: {(w.get('trend_alarm') or {}).get('opis', '–')}",
             f"Analogia 2021/22: {sum(a['trafienie'] for a in w['analogia'])} z {len(w['analogia'])} kamieni milowych ma odpowiednik."]
    tekst = "\n".join([temat, "", *[f"- {x}" for x in linie], "",
                       "Ten mail przychodzi raz w tygodniu, żebyś wiedział, że system działa. Alarmy przychodzą osobno, od razu.",
                       *([f"Pulpit (aktualizowany co godzinę): {url}", f"Metodyka: {url.rstrip('/')}/metodyka.html"] if url else []),
                       "", "Błąd? Odpowiedz na ten mail jednym zdaniem."])
    s = round(900 * (1 - max(0.0, min(100.0, w["indeks"])) / 100))
    obrazek = ""
    try:
        import obraz  # noqa: E402
        _OBRAZY["licznik"] = obraz.licznik_png(w["indeks"], slownik.progi, s, prog.get("luzno", prog["nazwa"]))
        obrazek = (f'<img src="cid:licznik" width="600" style="width:100%;max-width:600px;height:auto;display:block;margin:6px auto 4px;border:0" '
                   f'alt="Współczynnik wpierdolu {w["indeks"]:.0f}/100">')
    except Exception as ex:  # noqa: BLE001
        print("Obrazek licznika: pominięty,", ex)
    przycisk = (f'<a href="{e(url)}" style="display:inline-block;background:{T["ph"]};color:{T["inv"]};text-decoration:none;'
                f'font-weight:bold;padding:10px 18px;letter-spacing:2px">&gt; OTWÓRZ PULPIT</a>'
                f'<div style="font-size:12px;margin-top:8px"><a href="{e(url.rstrip("/"))}/metodyka.html" style="color:{T["ph"]}">Metodyka i jak zgłosić błąd</a></div>') if url else ""
    srodek = (_wiersz(f'<div style="font-size:11px;color:{T["ph2"]}">RAPORT TYGODNIOWY · {e(_data(w["wygenerowano"]))}</div>{obrazek}', "text-align:center")
              + _wiersz(_zakladka("TYDZIEŃ W SKRÓCIE") + "".join(f'<div style="margin-bottom:4px"><span style="color:{T["ph2"]}">&gt;</span> {e(x)}</div>' for x in linie))
              + _wiersz(f'<div style="color:{T["ph2"]};font-size:12px;margin-bottom:12px">Ten mail przychodzi raz w tygodniu, żebyś wiedział, że system działa. '
                        f'Alarmy (spiętrzenie sygnałów, sygnał krytyczny, alarm trendu) przychodzą osobno, od razu. Na co dzień zaglądaj na pulpit.</div>{przycisk}',
                        "text-align:center"))
    return temat, tekst, _ramka(srodek, "WCZESNE OSTRZEŻENIE · RAPORT TYGODNIOWY")


def skonfigurowana() -> bool:
    return all(os.environ.get(k) for k in ("SMTP_USER", "SMTP_PASS", "MAIL_DO"))


def zbuduj_krytyczny(sygnaly: list[dict], w: dict) -> tuple[str, str, str]:
    temat = "SYGNAŁ KRYTYCZNY: " + "; ".join(k["nazwa"] for k in sygnaly)
    url = os.environ.get("SITE_URL", "")
    linie = [temat, "",
             "Co najmniej 2 niezależne redakcje z oceną A lub B opisały w ciągu 24 h zdarzenie z listy sygnałów krytycznych wobec Polski lub krajów bałtyckich.",
             "Sprawdź komunikaty Rządowego Centrum Bezpieczeństwa (gov.pl/web/rcb) i Alert RCB w telefonie. Ten mail nie jest komunikatem władz.", ""]
    for k in sygnaly:
        linie.append(f"{k['nazwa']} ({k['grup']} redakcje):")
        linie += [f"- {p['tytul']} ({p['wydawca']})\n  {p['link']}" for p in k["przyklady"]]
        linie.append("")
    linie.append(f"Stan ogólny: {w['prog']['nazwa'].lower()}, indeks {w['indeks']:.0f}/100, spiętrzenie: {w['zbieznosc']['nazwa'].lower()}.")
    if url:
        linie.append(f"Pełny obraz: {url}")
    tekst = "\n".join(linie)
    blok = "".join(
        f'<h3 style="margin:16px 0 6px;color:#b0241c">{e(k["nazwa"])} · {k["grup"]} redakcje</h3><ul style="margin:0;padding-left:18px">'
        + "".join(f'<li style="margin-bottom:6px"><a href="{e(p["link"])}" style="color:#1d4f91">{e(p["tytul"])}</a> <span style="color:#566573">({e(p["wydawca"])})</span></li>' for p in k["przyklady"])
        + "</ul>" for k in sygnaly)
    blok = blok.replace("color:#b0241c", f"color:{T['ph']}").replace("color:#1d4f91", f"color:{T['ph']}").replace("color:#566573", f"color:{T['ph2']}")
    html = _ramka(_wiersz(f'<div style="background:{T["ph"]};color:{T["inv"]};padding:6px 10px;font-weight:bold;font-size:18px">&#9888; SYGNAŁ KRYTYCZNY</div>')
                  + _wiersz(f'<p style="margin:0 0 8px">{e(linie[2])}</p><p style="margin:0 0 8px;font-weight:bold">{e(linie[3])}</p>{blok}'
                            f'<p style="margin:16px 0 0;color:{T["ph2"]};font-size:13px">{e(linie[-2] if url else linie[-1])}</p>'))
    return temat, tekst, html


def zbuduj_trend(w: dict) -> tuple[str, str, str]:
    ta = w["trend_alarm"]
    temat = f"Trend wzrostowy: indeks od tygodnia wyraźnie powyżej normy ({ta['nadwyzka_7d']:+.0f} pkt)"
    url = os.environ.get("SITE_URL", "")
    linie = [temat, "",
             "Indeks zagrożenia od kilku dni rośnie powoli, ale stale. Żaden pojedynczy dzień nie przekroczył progu alarmu, "
             "ale suma nadwyżek ponad normę z ostatnich 30 dni przekroczyła próg. Tak narastała sytuacja jesienią 2021.",
             f"Szczegóły: {ta['opis']}",
             f"Dziś: {w['prog']['nazwa'].lower()}, indeks {w['indeks']:.0f}/100, spiętrzenie: {w['zbieznosc']['nazwa'].lower()}.",
             "Warto czytać skrót codziennie i sprawdzić plan rodzinny. To nie jest komunikat władz; oficjalne alerty: RCB."]
    if url:
        linie.append(f"Pełny obraz i wykres: {url}")
    tekst = "\n".join(linie)
    html = _ramka(_wiersz(f'<div style="background:{T["ph"]};color:{T["inv"]};padding:6px 10px;font-weight:bold;font-size:16px">&#9888; {e(temat.upper())}</div>')
                  + _wiersz("".join(f'<p style="margin:0 0 8px">&gt; {e(l)}</p>' for l in linie[2:])))
    return temat, tekst, html


def admin() -> list[str]:
    """Odbiorca maili administracyjnych (przegląd źródeł): MAIL_ADMIN albo nadawca."""
    a = os.environ.get("MAIL_ADMIN") or os.environ.get("SMTP_USER", "")
    return [x.strip() for x in a.split(",") if x.strip()]


def zbuduj_przeglad_zrodel(wynik: dict) -> tuple[str, str, str]:
    zm, uw = wynik["zmiany"], wynik["uwagi"]
    temat = f"Przegląd źródeł: {len(zm)} {'zmiana' if len(zm) == 1 else 'zmiany' if 1 < len(zm) < 5 else 'zmian'}"
    linie = [temat, "", "Zmiany wprowadzone automatycznie (reguły w app/utrzymanie.py):"]
    linie += [f"- {z['nazwa']}: {z['z']} -> {z['na']}. Powód: {z['powod']}." for z in zm] or ["- brak"]
    if uw:
        linie += ["", "Do wiadomości:"] + [f"- {u}" for u in uw]
    linie += ["", "Cofnięcie zmiany: napisz do Claude'a w repo projektu „przywróć <źródło>” albo uruchom",
              "python ostrzezenie.py zrodla status <id> aktywne. Ocen A–F i odblokowań aplikacja nie zmienia sama."]
    tekst = "\n".join(linie)
    html = _ramka(_wiersz("".join(f'<p style="margin:0 0 8px">{e(l)}</p>' if l else "" for l in linie)), "WCZESNE OSTRZEŻENIE · PRZEGLĄD ŹRÓDEŁ")
    return temat, tekst, html


def wyslij(temat: str, tekst: str, html: str, pilne: bool = False, odbiorcy: list[str] | None = None) -> bool:
    if not skonfigurowana():
        print("Mail: pominięty (brak SMTP_USER, SMTP_PASS albo MAIL_DO)")
        return False
    nadawca = os.environ["SMTP_USER"]
    odbiorcy = odbiorcy or [a.strip() for a in os.environ["MAIL_DO"].split(",") if a.strip()]
    m = EmailMessage()
    m["Subject"] = temat
    m["From"] = formataddr(("Wczesne Ostrzeżenie", nadawca))
    m["To"] = nadawca          # odbiorcy w BCC: nie widzą swoich adresów nawzajem
    m["Bcc"] = ", ".join(odbiorcy)
    if pilne:
        m["X-Priority"] = "1"
        m["Importance"] = "high"
    m.set_content(tekst)
    m.add_alternative(html, subtype="html")
    czesc_html = m.get_payload()[1]
    for cid, dane in _OBRAZY.items():
        if f"cid:{cid}" in html:
            czesc_html.add_related(dane, maintype="image", subtype="png", cid=f"<{cid}>", disposition="inline", filename=f"{cid}.png")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    try:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
            s.login(nadawca, os.environ["SMTP_PASS"])
            s.send_message(m)
        print(f"Mail wysłany do {len(odbiorcy)} odbiorców: {temat}")
        return True
    except Exception as ex:  # noqa: BLE001  — błąd poczty nie może zatrzymać aktualizacji strony
        print("Mail błąd:", type(ex).__name__, ex)
        return False
