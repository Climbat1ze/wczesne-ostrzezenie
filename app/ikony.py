"""Ikona aplikacji na pulpit telefonu (Android, iPhone) i manifest strony.

Pliki w strona/: ikona-192.png, ikona-512.png, ikona-maskable-512.png (Android przycina do koła lub kształtu
producenta, dlatego znak ma margines), apple-touch-icon.png (iPhone, 180 px), favicon.png (karta przeglądarki),
manifest.webmanifest (nazwa, kolory, otwieranie na pełnym ekranie bez paska przeglądarki).
Znak: koniczyna radiacji w kolorze luminoforu terminala (#4dff91) na ciemnym ekranie, jak w nagłówku strony.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

TLO, EKRAN, PH, DIM = "#030a05", "#071a0e", "#4dff91", "#1d8a4b"
NAZWA = "Wczesne Ostrzeżenie"
KROTKA = "Ostrzeżenie"


def _ikona(rozmiar: int, margines: float) -> Image.Image:
    """Rysuje w 4-krotnej rozdzielczości i zmniejsza (gładkie krawędzie). margines: część boku na brzeg."""
    s = rozmiar * 4
    im = Image.new("RGB", (s, s), TLO)
    d = ImageDraw.Draw(im)
    c = s / 2
    r = s * (0.5 - margines)                      # promień tarczy
    d.ellipse([c - r, c - r, c + r, c + r], fill=EKRAN, outline=DIM, width=max(2, int(s * 0.012)))
    # linie skanowania jak na ekranie terminala
    for y in range(int(c - r), int(c + r), max(4, s // 64)):
        pol = math.sqrt(max(0.0, r * r - (y - c) ** 2)) * 0.97   # cięciwa koła: linie tylko wewnątrz tarczy
        d.line([(c - pol, y), (c + pol, y)], fill="#06150b", width=max(1, s // 256))
    d.ellipse([c - r, c - r, c + r, c + r], outline=DIM, width=max(2, int(s * 0.012)))
    # koniczyna radiacji: 3 wycinki po 60 stopni co 120, środek i odstęp
    rz, rw, rs = r * 0.82, r * 0.24, r * 0.15
    for k in range(3):
        start = -90 - 30 + k * 120 + 180          # pierwszy listek u dołu, jak w znaku ostrzegawczym
        d.pieslice([c - rz, c - rz, c + rz, c + rz], start, start + 60, fill=PH)
    d.ellipse([c - rw, c - rw, c + rw, c + rw], fill=EKRAN)
    d.ellipse([c - rs, c - rs, c + rs, c + rs], fill=PH)
    return im.resize((rozmiar, rozmiar), Image.LANCZOS)


def zapisz(katalog: Path) -> list[str]:
    katalog.mkdir(exist_ok=True)
    pliki = {
        "ikona-192.png": _ikona(192, 0.06),
        "ikona-512.png": _ikona(512, 0.06),
        "ikona-maskable-512.png": _ikona(512, 0.16),   # strefa bezpieczna Androida: 80% środka
        "apple-touch-icon.png": _ikona(180, 0.10),
        "favicon.png": _ikona(64, 0.02),
    }
    for nazwa, im in pliki.items():
        im.save(katalog / nazwa, optimize=True)
    manifest = {
        "name": NAZWA, "short_name": KROTKA, "lang": "pl",
        "description": "Sygnały zagrożenia wobec Polski, Bałtów i krajów nordyckich z ocenionych źródeł, odczyt co godzinę.",
        "start_url": "./", "scope": "./", "display": "standalone", "orientation": "portrait",
        "background_color": TLO, "theme_color": TLO,
        "icons": [
            {"src": "ikona-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "ikona-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "ikona-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    (katalog / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return [*pliki, "manifest.webmanifest"]


GLOWA = ('<link rel="manifest" href="manifest.webmanifest">\n'
         f'<meta name="theme-color" content="{TLO}">\n'
         '<link rel="icon" type="image/png" href="favicon.png">\n'
         '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
         '<meta name="apple-mobile-web-app-capable" content="yes">\n'
         '<meta name="mobile-web-app-capable" content="yes">\n'
         f'<meta name="apple-mobile-web-app-title" content="{KROTKA}">\n'
         '<meta name="apple-mobile-web-app-status-bar-style" content="black">\n')


if __name__ == "__main__":
    import sys
    print(zapisz(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "strona"))
