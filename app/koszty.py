"""Blokady kosztów i dziennik zużycia.

- Dzienny budżet zapytań do Claude (`CLAUDE_BUDZET_DZIENNY`, domyślnie 150). Po wyczerpaniu: nagłówki zostają
  w oryginale, jeden mail do MAIL_ADMIN na dobę.
- Wyłącznik awaryjny `CLAUDE_WYLACZ=1`: żadnych wywołań Claude (tłumaczenie, oceny, przeglądy).
- Limit alarmów mailem do MAIL_DO (`ALARMY_DZIENNIE`, domyślnie 3 na dobę). Kolejne trafiają do kolejki i są
  doklejane do następnego wysłanego alarmu albo wysyłane zbiorczo o godzinie raportu (`STATUS_GODZINY`).
- Dziennik przebiegów i maili do raportu tygodniowego dla administratora.

Doba liczona po czasie warszawskim. Pliki stanu w app/dane (gałąź `dane`). Nic tu nie wypisuje adresów e-mail.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

WAW = ZoneInfo("Europe/Warsaw")
DANE = Path(__file__).resolve().parent / "dane"
BUDZET_DOMYSLNY = 150
ALARMY_DOMYSLNIE = 3


# ---------------------------------------------------------------- narzędzia

def _dzis() -> str:
    return dt.datetime.now(WAW).date().isoformat()


def _czytaj(nazwa: str, domyslnie):
    try:
        with open(DANE / nazwa, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return domyslnie


def _zapisz(nazwa: str, obj):
    DANE.mkdir(parents=True, exist_ok=True)
    tmp = DANE / (nazwa + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    tmp.replace(DANE / nazwa)


def _dopisz(nazwa: str, wpis: dict, zachowaj_dni: int = 60):
    DANE.mkdir(parents=True, exist_ok=True)
    p = DANE / nazwa
    granica = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=zachowaj_dni)).isoformat()
    stare = []
    if p.exists():
        with open(p, encoding="utf-8") as f:
            stare = [json.loads(l) for l in f if l.strip()]
    stare = [x for x in stare if x.get("ts", "") >= granica] + [wpis]
    with open(p, "w", encoding="utf-8") as f:
        for x in stare:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


def _czytaj_jsonl(nazwa: str) -> list[dict]:
    p = DANE / nazwa
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _int_env(nazwa: str, domyslnie: int) -> int:
    try:
        return max(0, int(os.environ.get(nazwa, "") or domyslnie))
    except ValueError:
        return domyslnie


# ---------------------------------------------------------------- budżet Claude

def wylaczone() -> bool:
    return os.environ.get("CLAUDE_WYLACZ", "").strip() == "1"


def limit_dzienny() -> int:
    return _int_env("CLAUDE_BUDZET_DZIENNY", BUDZET_DOMYSLNY)


def _stan_budzetu() -> dict:
    s = _czytaj("budzet.json", {})
    if s.get("data") != _dzis():
        historia = s.get("historia", {})
        if s.get("data"):
            historia[s["data"]] = s.get("wywolania", 0)
        historia = dict(sorted(historia.items())[-31:])
        s = {"data": _dzis(), "wywolania": 0, "mail_wyczerpany": False, "historia": historia}
    return s


def przydziel(ile: int) -> int:
    """Rezerwuje do `ile` wywołań Claude z dziennego budżetu. Zwraca liczbę przyznanych (0 przy wyłączniku)."""
    if ile <= 0 or wylaczone():
        return 0
    s = _stan_budzetu()
    wolne = max(0, limit_dzienny() - s["wywolania"])
    przyznane = min(ile, wolne)
    s["wywolania"] += przyznane
    if przyznane < ile and not s.get("mail_wyczerpany"):
        s["mail_wyczerpany"] = True
        _zapisz("budzet.json", s)
        _mail_budzet_wyczerpany(s["wywolania"])
    _zapisz("budzet.json", s)
    return przyznane


def zwolnij(ile: int):
    """Oddaje niewykorzystane wywołania (np. gdy zapytanie się nie odbyło)."""
    if ile <= 0:
        return
    s = _stan_budzetu()
    s["wywolania"] = max(0, s["wywolania"] - ile)
    _zapisz("budzet.json", s)


def zuzycie_dzis() -> int:
    return _stan_budzetu()["wywolania"]


def _mail_budzet_wyczerpany(wykorzystane: int):
    print(f"Budżet Claude wyczerpany: {wykorzystane}/{limit_dzienny()} wywołań dziś. Nagłówki zostają w oryginale do północy.")
    try:
        import poczta  # noqa: E402
        tekst = (f"Dzienny budżet zapytań do Claude jest wyczerpany ({wykorzystane} z {limit_dzienny()}).\n"
                 "Do północy (czas warszawski) nagłówki zostają w oryginale, a oceny trafności są pomijane.\n"
                 "Zmiana limitu: zmienna repozytorium CLAUDE_BUDZET_DZIENNY. Wyłącznik: CLAUDE_WYLACZ=1.")
        poczta.wyslij("Budżet Claude wyczerpany na dziś", tekst,
                      poczta.ramka_tekstu(tekst, "WCZESNE OSTRZEŻENIE · BUDŻET"), odbiorcy=poczta.admin())
        zapisz_mail("admin", "budżet wyczerpany")
    except Exception as ex:  # noqa: BLE001  — brak maila nie może zatrzymać przebiegu
        print("Mail o budżecie: nie wysłano,", type(ex).__name__)


# ---------------------------------------------------------------- limit alarmów

def limit_alarmow() -> int:
    return _int_env("ALARMY_DZIENNIE", ALARMY_DOMYSLNIE)


def alarmy_dzis() -> int:
    d = _dzis()
    return sum(1 for m in _czytaj_jsonl("maile.jsonl") if m.get("typ") == "alarm" and m.get("dzien") == d)


def zapisz_mail(typ: str, temat: str):
    """Dziennik maili: typ (alarm, raport, admin, zbiorczy), bez adresów."""
    _dopisz("maile.jsonl", {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                            "dzien": _dzis(), "typ": typ, "temat": temat[:120]})


def _kolejka() -> list[dict]:
    return _czytaj("kolejka_alarmow.json", [])


def _zapisz_alarm(temat: str, rodzaj: str, status: str):
    """Dziennik alarmów do ocen właściciela (linki trafny/pomyłka w raporcie administracyjnym)."""
    import samouczenie  # noqa: E402
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    _dopisz("alarmy.jsonl", {"ts": ts, "id": samouczenie.id_alarmu(ts, temat), "rodzaj": rodzaj, "temat": temat[:160],
                             "status": status}, zachowaj_dni=90)


def wyslij_alarm(temat: str, tekst: str, html: str, rodzaj: str) -> str:
    """Wysyła alarm do MAIL_DO z poszanowaniem limitu dziennego. Zwraca 'wyslany', 'w_kolejce' albo 'blad'."""
    wynik = _wyslij_alarm(temat, tekst, html, rodzaj)
    _zapisz_alarm(temat, rodzaj, wynik)
    return wynik


def _wyslij_alarm(temat: str, tekst: str, html: str, rodzaj: str) -> str:
    import poczta  # noqa: E402
    kolejka = _kolejka()
    if alarmy_dzis() >= limit_alarmow():
        kolejka.append({"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "rodzaj": rodzaj,
                        "temat": temat, "tekst": tekst[:2000]})
        _zapisz("kolejka_alarmow.json", kolejka)
        print(f"Alarm wstrzymany (limit {limit_alarmow()} na dobę): {temat}")
        return "w_kolejce"
    if kolejka:
        dopisek = _opis_kolejki(kolejka)
        tekst = tekst + "\n\n" + dopisek
        html = html.replace("</body>", poczta.blok_wstrzymanych(kolejka) + "</body>", 1)
    if poczta.wyslij(temat, tekst, html, pilne=True):
        zapisz_mail("alarm", temat)
        if kolejka:
            _zapisz("kolejka_alarmow.json", [])
        return "wyslany"
    return "blad"


def _opis_kolejki(kolejka: list[dict]) -> str:
    return "Wcześniej wstrzymane alarmy (limit dzienny):\n" + "\n".join(f"- {k['ts'][:16]} UTC: {k['temat']}" for k in kolejka)


def oproznij_kolejke(godzina_raportu: bool) -> bool:
    """O godzinie raportu wysyła zbiorczo wstrzymane alarmy, jeśli dzisiejszy limit na to pozwala."""
    kolejka = _kolejka()
    if not kolejka or not godzina_raportu or alarmy_dzis() >= limit_alarmow():
        return False
    import poczta  # noqa: E402
    temat = f"Zbiorczo: {len(kolejka)} wstrzymanych alarmów"
    tekst = _opis_kolejki(kolejka) + "\n\n" + "\n\n".join(k["tekst"] for k in kolejka)
    if poczta.wyslij(temat, tekst, poczta.ramka_tekstu(tekst, "WCZESNE OSTRZEŻENIE · ALARMY ZBIORCZO"), pilne=True):
        zapisz_mail("alarm", temat)
        _zapisz("kolejka_alarmow.json", [])
        return True
    return False


# ---------------------------------------------------------------- dziennik przebiegów i raport

def zapisz_przebieg(sekundy: float, kanaly_ok: int | None, kanaly_razem: int | None, **dodatkowe):
    _dopisz("przebiegi.jsonl", {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                                "sekundy": round(sekundy, 1), "kanaly_ok": kanaly_ok, "kanaly_razem": kanaly_razem,
                                "claude_dzis": zuzycie_dzis(), "run_id": os.environ.get("GITHUB_RUN_ID"), **dodatkowe})


def raport_7dni() -> dict:
    """Zużycie z 7 dni do poniedziałkowego maila administratora."""
    granica_ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat()
    granica_d = (dt.datetime.now(WAW).date() - dt.timedelta(days=7)).isoformat()
    s = _stan_budzetu()
    dni = {d: n for d, n in s.get("historia", {}).items() if d > granica_d}
    dni[s["data"]] = s["wywolania"]
    maile = [m for m in _czytaj_jsonl("maile.jsonl") if m.get("ts", "") >= granica_ts]
    po_typie: dict[str, int] = {}
    for m in maile:
        po_typie[m["typ"]] = po_typie.get(m["typ"], 0) + 1
    przebiegi = [p for p in _czytaj_jsonl("przebiegi.jsonl") if p.get("ts", "") >= granica_ts]
    czasy = [p["sekundy"] for p in przebiegi if p.get("sekundy") is not None]
    return {
        "claude_7d": sum(dni.values()), "claude_dni": dni, "claude_limit": limit_dzienny(), "claude_wylaczone": wylaczone(),
        "maile_7d": len(maile), "maile_po_typie": po_typie, "alarmy_w_kolejce": len(_kolejka()),
        "przebiegi_7d": len(przebiegi), "czas_sredni_s": round(sum(czasy) / len(czasy), 1) if czasy else None,
        "czas_max_s": max(czasy) if czasy else None, "minuty_actions_7d": round(sum(czasy) / 60, 1) if czasy else None,
    }
