"""Strażnik zakresu zmian: progi alarmów i wagi kategorii zmienia tylko właściciel.

Porównuje chronione pola `app/wskazniki.yaml` z wersją bazową (gałąź docelowa PR) i kończy się błędem, jeśli się różnią.
Chronione: waga, flaga „wysoka” i flaga „tylko_przeciwnik” każdej kategorii, lista kategorii, progi poziomów, mnożniki geografii,
nazwy sygnałów krytycznych. Wolno zmieniać: wzorce, wykluczenia, opisy, analogię, źródła.

Użycie: python app/straznik.py --baza origin/main
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

PLIK = "app/wskazniki.yaml"


def chronione(d: dict) -> dict:
    return {
        "kategorie": sorted(d["kategorie"]),
        "wagi": {k: v.get("waga") for k, v in d["kategorie"].items()},
        "wysokie": {k: bool(v.get("wysoka")) for k, v in d["kategorie"].items()},
        "propaganda": {k: bool(v.get("propaganda_jako_sygnal")) for k, v in d["kategorie"].items()},
        "tylko_przeciwnik": {k: bool(v.get("tylko_przeciwnik")) for k, v in d["kategorie"].items()},
        "progi": [{"od": p["od"], "kolor": p["kolor"]} for p in d.get("progi", [])],
        "geografia": {k: v.get("mnoznik") for k, v in d.get("geografia", {}).items()},
        "krytyczne": [k["nazwa"] for k in d.get("sygnaly_krytyczne", [])],
        "utrzymanie_zrodel": d.get("utrzymanie_zrodel"),
    }


def roznice(baza: dict, teraz: dict) -> list[str]:
    a, b = chronione(baza), chronione(teraz)
    # pole chronione od wersji 2.0: porównujemy, gdy wersja bazowa już je zna (pierwsze wprowadzenie zatwierdził właściciel)
    if not any(a["tylko_przeciwnik"].values()):
        a.pop("tylko_przeciwnik")
    return [f"{k}: {a[k]!r} → {b[k]!r}" for k in a if a[k] != b[k]]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baza", default="origin/main", help="referencja git z wersją bazową")
    a = ap.parse_args(argv)
    try:
        tekst_bazy = subprocess.run(["git", "show", f"{a.baza}:{PLIK}"], capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        print(f"Strażnik: brak {PLIK} w {a.baza}, pomijam porównanie")
        return 0
    r = roznice(yaml.safe_load(tekst_bazy), yaml.safe_load(Path(PLIK).read_text(encoding="utf-8")))
    if r:
        print("Strażnik: ZMIANA CHRONIONYCH PÓL (progi, wagi i flagi kategorii zmienia tylko właściciel):")
        for x in r:
            print(" -", x[:300])
        return 1
    print("Strażnik: progi i wagi bez zmian")
    return 0


if __name__ == "__main__":
    sys.exit(main())
