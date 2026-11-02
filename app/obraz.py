"""Obrazek do maila: licznik współczynnika wpierdolu (fuck-o-meter) i zegar zagłady jako PNG.

Gmail nie pokazuje SVG ani stylów, ale pokazuje obrazki wklejone w treść (Content-ID).
Rysowane Pillow w podwójnej rozdzielczości i zmniejszane (gładkie krawędzie). Bez plików z zewnątrz.
"""
from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG, EKRAN, PH, PH2, DIM, FAINT, INV = "#030a05", "#071a0e", "#4dff91", "#33d673", "#1d8a4b", "#0f3d22", "#021007"
SKALA = 2
FONTY = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf", "/System/Library/Fonts/Menlo.ttc", "C:/Windows/Fonts/consolab.ttf"]


def _font(rozmiar: int):
    for f in FONTY:
        if Path(f).exists():
            return ImageFont.truetype(f, rozmiar * SKALA)
    return ImageFont.load_default(size=rozmiar * SKALA)


def _mieszaj(kolor: str, alfa: float) -> tuple:
    a = tuple(int(kolor[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(EKRAN[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(round(b[k] + (a[k] - b[k]) * alfa) for k in range(3))


def _tekst(d: ImageDraw.ImageDraw, xy, txt, rozmiar, kolor=PH, kotwica="mm"):
    d.text((xy[0] * SKALA, xy[1] * SKALA), txt, font=_font(rozmiar), fill=kolor, anchor=kotwica)


def licznik_png(indeks: float, progi: list[dict], sekundy: int, poziom: str) -> bytes:
    W, H = 640, 300
    img = Image.new("RGB", (W * SKALA, H * SKALA), EKRAN)
    d = ImageDraw.Draw(img)
    s = SKALA
    d.rectangle([2 * s, 2 * s, (W - 3) * s, (H - 3) * s], outline=DIM, width=2 * s)

    # licznik WW (lewa część)
    cx, cy, r = 205, 200, 140
    _tekst(d, (cx, 24), "WSPÓŁCZYNNIK WPIERDOLU", 15, PH2)
    _tekst(d, (cx, 42), "aka FUCK-O-METER", 11, DIM)
    granice = [p["od"] for p in progi] + [100]
    box = [(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s]
    for i in range(len(progi)):
        a1 = 180 + 180 * granice[i] / 100
        a2 = 180 + 180 * granice[i + 1] / 100
        d.arc(box, a1, a2, fill=_mieszaj(PH, 0.25 + 0.25 * i), width=18 * s)
    for v in range(0, 101, 5):
        a = math.radians(180 + 180 * v / 100)
        r1, r2 = r - 14, r - (26 if v % 10 == 0 else 20)
        d.line([((cx + r1 * math.cos(a)) * s, (cy + r1 * math.sin(a)) * s),
                ((cx + r2 * math.cos(a)) * s, (cy + r2 * math.sin(a)) * s)], fill=PH2, width=(2 if v % 10 == 0 else 1) * s)
    for v in granice:
        a = math.radians(180 + 180 * v / 100)
        _tekst(d, (cx + (r - 40) * math.cos(a), cy + (r - 40) * math.sin(a)), str(v), 12, PH2)
    a = math.radians(180 + 180 * max(0, min(100, indeks)) / 100)
    tip = (cx + (r - 28) * math.cos(a), cy + (r - 28) * math.sin(a))
    bok = (math.cos(a + math.pi / 2) * 6, math.sin(a + math.pi / 2) * 6)
    d.polygon([((cx + bok[0]) * s, (cy + bok[1]) * s), ((cx - bok[0]) * s, (cy - bok[1]) * s), (tip[0] * s, tip[1] * s)], fill=PH)
    d.ellipse([(cx - 11) * s, (cy - 11) * s, (cx + 11) * s, (cy + 11) * s], fill=EKRAN, outline=PH, width=3 * s)
    _tekst(d, (cx, cy - 52), f"{indeks:.0f}", 44, PH)
    tw = d.textlength(poziom.upper(), font=_font(22)) / s
    if indeks >= 70:
        d.rectangle([(cx - tw / 2 - 8) * s, (cy + 26) * s, (cx + tw / 2 + 8) * s, (cy + 58) * s], fill=PH)
        _tekst(d, (cx, cy + 42), poziom.upper(), 22, INV)
    else:
        _tekst(d, (cx, cy + 42), poziom.upper(), 22, PH)
    _tekst(d, (cx, cy + 78), "0 PIJ KAWĘ · 30 PLECAK · 50 BAK · 70 SCHRON", 10, DIM)

    # zegar zagłady (prawa część)
    zx, zy, zr = 505, 140, 82
    _tekst(d, (zx, 24), "ZEGAR ZAGŁADY", 15, PH2)
    d.ellipse([(zx - zr) * s, (zy - zr) * s, (zx + zr) * s, (zy + zr) * s], outline=PH, width=3 * s)
    d.pieslice([(zx - zr + 6) * s, (zy - zr + 6) * s, (zx + zr - 6) * s, (zy + zr - 6) * s], 180, 270, fill=FAINT)
    for i in range(60):
        a = math.radians(i * 6 - 90)
        r1 = zr - (14 if i % 5 == 0 else 8)
        d.line([((zx + r1 * math.cos(a)) * s, (zy + r1 * math.sin(a)) * s),
                ((zx + (zr - 3) * math.cos(a)) * s, (zy + (zr - 3) * math.sin(a)) * s)],
               fill=PH2, width=(3 if i % 5 == 0 else 1) * s)
    minuty = sekundy / 60
    am = math.radians((60 - minuty) * 6 - 90)
    ah = math.radians((11 + (60 - minuty) / 60) * 30 - 90)
    d.line([(zx * s, zy * s), ((zx + 46 * math.cos(ah)) * s, (zy + 46 * math.sin(ah)) * s)], fill=PH, width=6 * s)
    d.line([(zx * s, zy * s), ((zx + 68 * math.cos(am)) * s, (zy + 68 * math.sin(am)) * s)], fill=PH, width=3 * s)
    d.ellipse([(zx - 6) * s, (zy - 6) * s, (zx + 6) * s, (zy + 6) * s], fill=PH)
    _tekst(d, (zx, zy + zr + 26), f"{sekundy // 60} MIN {sekundy % 60:02d} S", 22, PH)
    _tekst(d, (zx, zy + zr + 48), "DO PÓŁNOCY", 11, DIM)

    img = img.resize((W, H), Image.LANCZOS)
    linie = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(linie)
    for y in range(0, H, 3):
        dl.line([(0, y), (W, y)], fill=(0, 0, 0, 55))
    img = Image.alpha_composite(img.convert("RGBA"), linie).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
