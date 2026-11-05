import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))


@pytest.fixture
def dane_tmp(tmp_path, monkeypatch):
    """Stan aplikacji w katalogu tymczasowym, bez prawdziwych maili."""
    import koszty
    import poczta
    monkeypatch.setattr(koszty, "DANE", tmp_path)
    wyslane = []

    def falszywa_wysylka(temat, tekst, html, pilne=False, odbiorcy=None):
        wyslane.append({"temat": temat, "tekst": tekst, "odbiorcy": odbiorcy})
        return True

    monkeypatch.setattr(poczta, "wyslij", falszywa_wysylka)
    for zmienna in ("CLAUDE_WYLACZ", "CLAUDE_BUDZET_DZIENNY", "CLAUDE_REZERWA", "ALARMY_DZIENNIE"):
        monkeypatch.delenv(zmienna, raising=False)
    return wyslane
