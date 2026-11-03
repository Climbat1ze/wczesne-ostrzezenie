"""Jedno miejsce wywołań Claude Code CLI na subskrypcji (CLAUDE_CODE_OAUTH_TOKEN).

Zasady: zawsze jawny --model i --tools "" (model nic nie uruchamia, tylko odpowiada tekstem), pusty katalog roboczy
(nie wczytuje CLAUDE.md repo), treść z RSS idzie przez stdin, nigdy przez powłokę ani argumenty polecenia.
Budżet i wyłącznik sprawdza wywołujący (koszty.przydziel).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile


def dostepny() -> bool:
    import koszty  # noqa: E402
    return not koszty.wylaczone() and bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")) and bool(shutil.which("claude"))


def zapytaj(system: str, tresc: str, model: str = "haiku", timeout: int = 240) -> tuple[bool, str]:
    """Zwraca (sukces, tekst odpowiedzi albo krótki opis błędu bez treści sekretów)."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}  # klucz API miałby pierwszeństwo przed subskrypcją
    polecenie = ["claude", "-p", "--model", model, "--tools", "", "--system-prompt", system,
                 "--output-format", "text", "--no-session-persistence"]
    with tempfile.TemporaryDirectory() as tmp:
        try:
            r = subprocess.run(polecenie, input=tresc, capture_output=True, text=True, timeout=timeout, cwd=tmp, env=env)
        except subprocess.TimeoutExpired:
            return False, "przekroczony czas"
        except OSError as ex:
            return False, type(ex).__name__
    if r.returncode != 0:
        return False, f"kod {r.returncode}: {(r.stderr or r.stdout)[-200:]}"
    return True, r.stdout
