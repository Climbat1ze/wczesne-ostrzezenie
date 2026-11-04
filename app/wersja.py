"""Wersja aplikacji (semver). Jedno źródło: plik app/WERSJA. Historia zmian: CHANGELOG.md, rejestr zgłoszeń zmian:
docs/change_requests.md. Zasada: MAJOR = nowy moduł albo zmiana sposobu liczenia WW, MINOR = nowa funkcja bez zmiany
liczenia, PATCH = poprawka wzorca, tekstu albo błędu."""
from __future__ import annotations

from pathlib import Path

PLIK = Path(__file__).resolve().parent / "WERSJA"


def wersja() -> str:
    try:
        return PLIK.read_text(encoding="utf-8").strip() or "0.0.0"
    except FileNotFoundError:
        return "0.0.0"


WERSJA = wersja()
