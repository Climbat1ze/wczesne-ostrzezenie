"""Bezpieczeństwo linków z kanałów RSS.

Warstwa 1, przy każdym przebiegu, lokalnie, bez sieci: każdy link z wpisu przechodzi kontrolę
(tylko http/https, bez adresu IP zamiast domeny, bez punycode, bez danych logowania w adresie,
bez niestandardowego portu, domena linku = domena kanału albo domena z pola `domeny_linkow` źródła,
domena spoza blokady z app/linki_blokada.yaml). Link, który nie przejdzie, zostaje zastąpiony
stroną główną redakcji (domena kanału), a powód trafia do dane/linki_odrzucone.jsonl.

Warstwa 2, raz w tygodniu (workflow linki-virustotal.yml): domeny kanałów i linków z ostatnich 7 dni
sprawdzane w VirusTotal (tylko odczyt raportu domeny, nic nie wysyłamy do skanowania).
Domeny ocenione jako groźne trafiają do app/linki_blokada.yaml (commit do main), wynik do issue.
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

APP = Path(__file__).resolve().parent
PLIK_BLOKADA = APP / "linki_blokada.yaml"
PLIK_ZRODLA = APP / "zrodla.yaml"

# Sufiksy dwuczłonowe, pod którymi domeną redakcji są trzy ostatnie człony (bbc.co.uk, x.com.pl).
_SUFIKSY_2 = {"waw.pl", "krakow.pl", "co.uk", "org.uk", "gov.uk", "ac.uk", "com.pl", "org.pl", "gov.pl", "net.pl", "com.ua",
              "gov.ua", "org.ua", "com.au", "co.jp", "gov.lv", "gov.lt", "gov.ee", "com.lv", "com.ee"}


def domena(url_lub_host: str) -> str:
    """Domena rejestrowana (np. news.err.ee -> err.ee, www.bbc.co.uk -> bbc.co.uk)."""
    host = url_lub_host
    if "/" in url_lub_host or ":" in url_lub_host:
        host = urllib.parse.urlsplit(url_lub_host).hostname or ""
    czlony = host.lower().strip(".").split(".")
    if len(czlony) >= 3 and ".".join(czlony[-2:]) in _SUFIKSY_2:
        return ".".join(czlony[-3:])
    return ".".join(czlony[-2:])


PLIK_WYJATKI = APP / "linki_wyjatki.yaml"


def wczytaj_wyjatki() -> dict:
    """Znane fałszywe alarmy VirusTotal (decyzja właściciela): nie blokują linków i nie zakładają issue."""
    if not PLIK_WYJATKI.exists():
        return {}
    d = yaml.safe_load(PLIK_WYJATKI.read_text(encoding="utf-8")) or {}
    return {x["domena"]: x for x in (d.get("domeny") or [])}


def wczytaj_blokade() -> dict:
    if not PLIK_BLOKADA.exists():
        return {}
    d = yaml.safe_load(PLIK_BLOKADA.read_text(encoding="utf-8")) or {}
    return {x["domena"]: x for x in (d.get("domeny") or [])}


_KONTEKST: dict | None = None


def _kontekst() -> dict:
    """Domeny dozwolone dla każdego źródła i blokada. Wczytywane raz na przebieg."""
    global _KONTEKST
    if _KONTEKST is None:
        zr = (yaml.safe_load(PLIK_ZRODLA.read_text(encoding="utf-8")) or {}).get("zrodla", [])
        _KONTEKST = {
            "zrodla": {z["id"]: {"dozwolone": {domena(z["url"]), *[domena(d) for d in z.get("domeny_linkow", [])]},
                                 "glowna": "https://" + (urllib.parse.urlsplit(z["url"]).hostname or "") + "/"}
                       for z in zr},
            "blokada": wczytaj_blokade(),
        }
    return _KONTEKST


def ocen_link(link: str, dozwolone: set[str], blokada: dict) -> str | None:
    """None = link w porządku, inaczej powód odrzucenia."""
    if not link:
        return None
    try:
        u = urllib.parse.urlsplit(link.strip())
        host = u.hostname or ""
        port = u.port
    except ValueError:
        return "adres nie do odczytania"
    if u.scheme not in ("http", "https"):
        return f"schemat {u.scheme or 'brak'}"
    if not host:
        return "brak domeny"
    if u.username or u.password or "@" in u.netloc:
        return "dane logowania w adresie"
    if port not in (None, 80, 443):
        return f"niestandardowy port {port}"
    try:
        ipaddress.ip_address(host)
        return "adres IP zamiast domeny"
    except ValueError:
        pass
    if any(c.startswith("xn--") for c in host.split(".")):
        return "domena w punycode"
    d = domena(host)
    if d in blokada:
        return f"domena zablokowana: {blokada[d].get('powod', 'VirusTotal')}"
    if dozwolone and d not in dozwolone:
        return f"domena {d} spoza domen źródła"
    return None


def zabezpiecz(wpis: dict, log: list | None = None) -> dict:
    """Podmienia podejrzany link na stronę główną redakcji. Zwraca ten sam słownik."""
    k = _kontekst()
    z = k["zrodla"].get(wpis.get("zrodlo"), {"dozwolone": set(), "glowna": ""})
    powod = ocen_link(wpis.get("link", ""), z["dozwolone"], k["blokada"])
    if powod:
        if log is not None:
            log.append({"id": wpis.get("id"), "zrodlo": wpis.get("zrodlo"), "link": wpis.get("link"), "powod": powod})
        wpis["link"] = z["glowna"]
        wpis["link_odrzucony"] = powod
    return wpis


def zapisz_odrzucone(dane: Path, log: list[dict]):
    """Dopisuje nowe odrzucenia (bez powtórek tego samego wpisu) do dane/linki_odrzucone.jsonl."""
    if not log:
        return 0
    p = dane / "linki_odrzucone.jsonl"
    znane = set()
    if p.exists():
        znane = {json.loads(l).get("id") for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}
    nowe = [x for x in log if x["id"] not in znane]
    if nowe:
        kiedy = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
        with open(p, "a", encoding="utf-8") as f:
            for x in nowe:
                f.write(json.dumps({**x, "kiedy": kiedy}, ensure_ascii=False) + "\n")
    return len(nowe)


# ---------------------------------------------------------------- VirusTotal (raz w tygodniu)

VT_API = "https://www.virustotal.com/api/v3/domains/"
PRZERWA_S = 15.5  # darmowe API: 4 zapytania na minutę


def raport_vt(d: str, klucz: str) -> dict:
    req = urllib.request.Request(VT_API + urllib.parse.quote(d), headers={"x-apikey": klucz, "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            a = json.load(r)["data"]["attributes"]
    except urllib.error.HTTPError as e:
        return {"domena": d, "blad": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"domena": d, "blad": type(e).__name__}
    s = a.get("last_analysis_stats", {})
    zle = sorted(k for k, v in (a.get("last_analysis_results") or {}).items() if v.get("category") in ("malicious", "suspicious"))
    return {"domena": d, "malicious": s.get("malicious", 0), "suspicious": s.get("suspicious", 0),
            "harmless": s.get("harmless", 0), "reputacja": a.get("reputation", 0), "silniki": zle[:8]}


def werdykt(r: dict) -> str:
    """groźna: co najmniej 2 silniki „malicious”; do sprawdzenia: 1 „malicious” albo co najmniej 2 „suspicious”."""
    if r.get("blad"):
        return "błąd"
    if r["malicious"] >= 2:
        return "groźna"
    if r["malicious"] == 1 or r["suspicious"] >= 2:
        return "do sprawdzenia"
    return "czysta"


def domeny_do_sprawdzenia(wpisy_jsonl: Path | None, dni: int = 7) -> list[str]:
    zr = (yaml.safe_load(PLIK_ZRODLA.read_text(encoding="utf-8")) or {}).get("zrodla", [])
    dom = {domena(z["url"]) for z in zr if z.get("status") != "zablokowane"}
    if wpisy_jsonl and wpisy_jsonl.exists():
        od = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=dni)
        for l in wpisy_jsonl.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            w = json.loads(l)
            try:
                if dt.datetime.fromisoformat(w["data"]) < od:
                    continue
            except (KeyError, ValueError):
                pass
            if w.get("link"):
                dom.add(domena(w["link"]))
    dom.discard("")
    return sorted(dom)


def skanuj(wpisy_jsonl: Path | None, wynik_md: Path, klucz: str, przerwa: float = PRZERWA_S) -> dict:
    domeny = domeny_do_sprawdzenia(wpisy_jsonl)
    wyjatki = wczytaj_wyjatki()
    print(f"VirusTotal: {len(domeny)} domen do sprawdzenia, znane fałszywe alarmy: {', '.join(sorted(wyjatki)) or 'brak'}")
    wyniki = []
    for i, d in enumerate(domeny):
        if i:
            time.sleep(przerwa)
        r = raport_vt(d, klucz)
        r["werdykt"] = werdykt(r)
        if d in wyjatki and r["werdykt"] in ("do sprawdzenia", "groźna"):
            r["werdykt_vt"], r["werdykt"] = r["werdykt"], "czysta"  # znany fałszywy alarm (app/linki_wyjatki.yaml)
            r["wyjatek"] = wyjatki[d].get("powod", "")
        wyniki.append(r)
        print(f"  {d}: {r['werdykt']}" + (f" ({r['blad']})" if r.get("blad") else f" (malicious {r['malicious']}, suspicious {r['suspicious']})"))

    grozne = [r for r in wyniki if r["werdykt"] == "groźna"]
    blokada = wczytaj_blokade()
    dzis = dt.date.today().isoformat()
    nowe_blokady = []
    for r in grozne:
        if r["domena"] not in blokada:
            blokada[r["domena"]] = {"domena": r["domena"], "od": dzis,
                                    "powod": f"VirusTotal: {r['malicious']} silników malicious ({', '.join(r['silniki'][:4])})"}
            nowe_blokady.append(r["domena"])
    if nowe_blokady:
        naglowek = ("# Domeny, których linków aplikacja nie pokazuje (zastępuje je stroną główną redakcji).\n"
                    "# Dopisuje workflow linki-virustotal.yml (co najmniej 2 silniki „malicious”). Odblokowanie: usuń wpis ręcznie.\n")
        PLIK_BLOKADA.write_text(naglowek + yaml.safe_dump({"domeny": sorted(blokada.values(), key=lambda x: x["domena"])},
                                                          allow_unicode=True, sort_keys=False), encoding="utf-8")

    licz = {k: sum(1 for r in wyniki if r["werdykt"] == k) for k in ("czysta", "do sprawdzenia", "groźna", "błąd")}
    linie = [f"Sprawdzono {len(wyniki)} domen (kanały źródeł i linki z ostatnich 7 dni) w VirusTotal, raport domeny, bez wysyłania adresów do skanowania.",
             "", f"Czyste: {licz['czysta']}. Do sprawdzenia: {licz['do sprawdzenia']}. Groźne: {licz['groźna']}. Błędy zapytania: {licz['błąd']}.", ""]
    for r in wyniki:
        if r["werdykt"] in ("groźna", "do sprawdzenia", "błąd"):
            szcz = r.get("blad") or f"malicious {r['malicious']}, suspicious {r['suspicious']}, reputacja {r['reputacja']}, silniki: {', '.join(r['silniki']) or 'brak'}"
            linie.append(f"- **{r['domena']}**: {r['werdykt']} ({szcz}). Raport: https://www.virustotal.com/gui/domain/{r['domena']}")
    znane = [r for r in wyniki if r.get("wyjatek")]
    if znane:
        linie += ["", "Znane fałszywe alarmy (app/linki_wyjatki.yaml, bez blokady i bez issue):"]
        linie += [f"- {r['domena']}: VirusTotal „{r['werdykt_vt']}” (malicious {r['malicious']}, suspicious {r['suspicious']}). {r['wyjatek']}" for r in znane]
    if nowe_blokady:
        linie += ["", f"Nowe blokady w `app/linki_blokada.yaml`: {', '.join(nowe_blokady)}. Linki z tych domen aplikacja zastępuje stroną główną redakcji."]
    linie += ["", "Reguła: groźna = co najmniej 2 silniki „malicious” (automatyczna blokada linków); do sprawdzenia = 1 silnik „malicious” albo co najmniej 2 „suspicious” (bez blokady, decyzja właściciela)."]
    wynik_md.write_text("\n".join(linie), encoding="utf-8")
    return {"licz": licz, "nowe_blokady": nowe_blokady, "wyniki": wyniki}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Cotygodniowe sprawdzenie domen w VirusTotal")
    p.add_argument("--wpisy", type=Path, default=APP / "dane" / "wpisy.jsonl")
    p.add_argument("--wynik", type=Path, required=True)
    a = p.parse_args()
    klucz = os.environ.get("VIRUSTOTAL_API_KEY", "")
    if not klucz:
        print("Brak sekretu VIRUSTOTAL_API_KEY: pomijam sprawdzenie.")
        raise SystemExit(0)
    w = skanuj(a.wpisy, a.wynik, klucz)
    print("Wynik:", w["licz"], "nowe blokady:", w["nowe_blokady"] or "brak")
