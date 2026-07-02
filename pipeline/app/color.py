"""Colour engine — a faithful Python port of the app's `lib/color.ts`.

This is the "honest" core: palette extraction, fashion-friendly colour naming,
and harmony scoring from real hue relationships. The judgment layer reuses it so
the stubbed verdict is grounded in what's actually in the photo — only the
language is canned, never the colour reasoning.
"""
from __future__ import annotations

from typing import List, Tuple


def hex_to_rgb(hexstr: str) -> Tuple[int, int, int]:
    h = hexstr.lstrip("#")
    if len(h) != 6:
        return (184, 168, 176)  # graceful default (#b8a8b0)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (184, 168, 176)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    def c(v: float) -> str:
        return format(max(0, min(255, round(v))), "02x")

    return f"#{c(r)}{c(g)}{c(b)}"


def rgb_to_hsl(r: float, g: float, b: float) -> Tuple[float, float, float]:
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    h = s = 0.0
    if mx != mn:
        d = mx - mn
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = ((g - b) / d + (6 if g < b else 0)) * 60
        elif mx == g:
            h = ((b - r) / d + 2) * 60
        else:
            h = ((r - g) / d + 4) * 60
    return (h, s * 100, l * 100)


def hex_to_hsl(hexstr: str) -> Tuple[float, float, float]:
    r, g, b = hex_to_rgb(hexstr)
    return rgb_to_hsl(r, g, b)


def color_name(hexstr: str) -> str:
    """Fashion-friendly colour name (ported 1:1 from color.ts)."""
    h, s, l = hex_to_hsl(hexstr)

    if l >= 96:
        return "white"
    if l >= 88 and s < 22:
        return "ivory"
    if l <= 12:
        return "noir"
    if s < 9:
        if l >= 72:
            return "dove gray"
        if l >= 45:
            return "stone"
        return "charcoal"
    if s < 22:
        if 60 <= h < 170:
            return "sage" if l >= 58 else "moss"
        if l >= 70:
            return "cream" if 20 <= h < 60 else "mist gray"
        if l >= 42:
            if 20 <= h < 60:
                return "taupe"
            if 170 <= h < 280:
                return "slate"
            return "heather"
        return "ink blue" if 180 <= h < 290 else "espresso"

    if h < 14 or h >= 345:
        if l >= 78:
            return "blush"
        if l >= 55:
            return "dusty rose"
        if s >= 65 and l >= 38:
            return "scarlet"
        return "rosewood"
    if h < 38:
        if l >= 78:
            return "shell pink" if h < 26 else "champagne"
        if l >= 50:
            return "terracotta"
        if l >= 34:
            return "rust"
        return "chestnut"
    if h < 52:
        if l >= 75:
            return "champagne"
        if l >= 50:
            return "camel"
        return "bronze"
    if h < 68:
        return "butter" if l >= 72 else "gold"
    if h < 96:
        if l >= 70:
            return "pistachio"
        return "olive" if l >= 42 else "forest"
    if h < 150:
        if l >= 72:
            return "mint"
        return "sage" if l >= 45 else "emerald"
    if h < 200:
        return "seafoam" if l >= 70 else "teal"
    if h < 230:
        if l >= 76:
            return "sky"
        return "denim blue" if l >= 50 else "navy"
    if h < 262:
        if l >= 74:
            return "periwinkle"
        return "indigo" if l >= 42 else "midnight"
    if h < 296:
        if l >= 76:
            return "lavender"
        return "violet" if l >= 45 else "plum"
    if l >= 76:
        return "rose"
    return "mauve" if l >= 48 else "berry"


def color_family(hexstr: str) -> str:
    """Coarse family used for preference memory (ported from color.ts)."""
    h, s, l = hex_to_hsl(hexstr)
    if s < 14:
        return "soft-neutral" if l >= 60 else "deep-neutral"
    if s < 26:
        return "warm-neutral"
    if h < 14 or h >= 330:
        return "rose"
    if h < 52:
        return "earth"
    if h < 68:
        return "gold"
    if h < 165:
        return "green"
    if h < 262:
        return "blue"
    return "plum"


def is_neutral(hexstr: str) -> bool:
    _, s, l = hex_to_hsl(hexstr)
    return s < 18 or l > 88 or l < 14


def harmony_score(hexes: List[str]) -> int:
    """0–100 score of how well a set of colours sits together (ported)."""
    colored = [c for c in hexes if not is_neutral(c)]
    neutrals = len(hexes) - len(colored)

    if len(colored) <= 1:
        return 84 + min(neutrals, 3) * 3

    hues = [hex_to_hsl(c)[0] for c in colored]
    total = pairs = 0
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            d = abs(hues[i] - hues[j])
            if d > 180:
                d = 360 - d
            if d <= 35:
                pair = 92
            elif d <= 70:
                pair = 78
            elif d <= 110:
                pair = 64
            elif d <= 145:
                pair = 72
            else:
                pair = 86
            total += pair
            pairs += 1
    score = total / pairs
    score += min(neutrals, 2) * 4
    return round(max(55, min(96, score)))


def extract_palette(image_bytes: bytes, count: int = 4) -> List[str]:
    """Extract a dominant palette from an image (ported from extractPalette).

    Pillow is imported lazily so the palette-only path (frontend pre-extracts on
    device and sends hexes) never needs the dependency.
    """
    try:
        import io

        from PIL import Image
    except Exception:  # pragma: no cover - only when a photo is actually sent
        return ["#b8a8b0"]

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA").resize((56, 56))
    except Exception:
        return ["#b8a8b0"]

    Q = 28
    buckets: dict[str, list] = {}
    for r, g, b, a in img.getdata():
        if a < 200:
            continue
        key = f"{round(r / Q)},{round(g / Q)},{round(b / Q)}"
        e = buckets.get(key)
        if e:
            e[0] += r
            e[1] += g
            e[2] += b
            e[3] += 1
        else:
            buckets[key] = [r, g, b, 1]

    entries = sorted(
        ({"hex": rgb_to_hex(e[0] / e[3], e[1] / e[3], e[2] / e[3]), "n": e[3]} for e in buckets.values()),
        key=lambda x: x["n"],
        reverse=True,
    )
    if not entries:
        return ["#b8a8b0"]

    non_white = [e for e in entries if hex_to_hsl(e["hex"])[2] < 94]
    if len(non_white) >= 2:
        entries = non_white

    picked: List[str] = []
    for e in entries:
        r1, g1, b1 = hex_to_rgb(e["hex"])
        distinct = all(
            (abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)) > 90
            for r2, g2, b2 in (hex_to_rgb(p) for p in picked)
        )
        if distinct:
            picked.append(e["hex"])
        if len(picked) >= count:
            break
    return picked or [entries[0]["hex"]]
