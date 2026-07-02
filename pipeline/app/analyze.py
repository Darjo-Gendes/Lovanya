"""Stage 2 — perception + judgment. THE swappable model boundary.

Every analyzer returns the same `Perception` / `Judgment` (and therefore the same
canonical contract), so switching models is a one-line config change
(config.MODEL). Today's default `HonestMockAnalyzer` ports the app's real colour
reasoning from lovanya/lib/ai/mock.ts — grounded scoring, canned language. The
`QwenAnalyzer` is the documented next step and is intentionally not wired.

The styling framework (the rubric + brand voice) is loaded from a FILE at
runtime — tuning the product is a text edit, never a code change.
"""
from __future__ import annotations

from typing import Protocol

from .. import config
from .color import (
    color_name,
    harmony_score,
    hex_to_hsl,
    is_neutral,
)
from .contracts import AnalyzeRequest, Judgment, Perception


# --- framework-as-file --------------------------------------------------------
def load_framework() -> str:
    try:
        with open(config.FRAMEWORK_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        # Missing framework is a soft failure for the mock; a real model that
        # depends on it should surface this instead.
        return ""


# --- small helpers (ported from mock.ts) --------------------------------------
def _hash(s: str) -> int:
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        if h & 0x80000000:  # emulate JS `| 0` (signed 32-bit) each step
            h -= 0x100000000
    return abs(h)


def _pick(arr: list, seed: int):
    return arr[seed % len(arr)]


def _clamp(v: float, lo: int, hi: int) -> int:
    return round(max(lo, min(hi, v)))


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


OCCASION_FORMALITY = {
    "work": 2.4, "class": 1.6, "casual": 1.2, "date": 2.4, "event": 2.8, "errands": 1.1,
}
_OCCASION_LABEL = {
    "work": "a work day", "class": "class", "casual": "a casual day",
    "date": "a date", "event": "an event", "errands": "errands",
}
HEADLINES_HIGH = [
    "This is genuinely lovely on you",
    "You found something special today",
    "Quiet confidence — it's all here",
]
HEADLINES_MID = [
    "This works — with one soft tweak it sings",
    "A solid look with lovely bones",
    "You're closer than you think",
]
CATEGORY_NOUNS = {
    "top": ["relaxed shirt", "soft blouse", "fine knit", "easy top"],
    "bottom": ["wide-leg trousers", "midi skirt", "tailored trousers", "relaxed jeans"],
    "dress": ["flowing dress", "wrap dress", "everyday dress"],
    "outerwear": ["soft blazer", "cardigan", "light coat"],
    "shoes": ["everyday flats", "block heels", "clean sneakers"],
    "bag": ["everyday tote", "crossbody"],
    "accessory": ["featherweight scarf", "silk scarf"],
}


def _occasion_label(o: str) -> str:
    return _OCCASION_LABEL.get(o, "today")


class Analyzer(Protocol):
    def perceive(self, palette: list[str]) -> Perception: ...
    def judge(self, perception: Perception, palette: list[str], ctx: AnalyzeRequest) -> Judgment: ...


class HonestMockAnalyzer:
    """GPU-free analyzer grounded in the real colour engine (ported mock.ts)."""

    def __init__(self, framework_text: str) -> None:
        self.framework = framework_text  # a real model injects this into its prompt

    def perceive(self, palette: list[str]) -> Perception:
        seed = _hash("|".join(palette))
        main = next((c for c in palette if not is_neutral(c)), palette[0] if palette else "#b8a8b0")
        l = hex_to_hsl(main)[2]

        weighted = [("top", 30), ("bottom", 22), ("dress", 12), ("outerwear", 12),
                    ("shoes", 10), ("bag", 8), ("accessory", 6)]
        total = sum(w for _, w in weighted)
        roll = seed % total
        category = "top"
        for c, w in weighted:
            if roll < w:
                category = c
                break
            roll -= w

        return Perception(
            category=category,  # type: ignore[arg-type]
            colors=palette[:3],
            warmth=2 if l < 38 else 1,
            formality=1 if (seed >> 5) % 3 == 0 else 2,
            subcategory=_pick(CATEGORY_NOUNS[category], seed >> 3),
        )

    def judge(self, perception: Perception, palette: list[str], ctx: AnalyzeRequest) -> Judgment:
        seed = _hash("".join(palette) + ctx.occasion)
        names = [color_name(c) for c in palette]
        neutrals = [c for c in palette if is_neutral(c)]
        colored = [c for c in palette if not is_neutral(c)]

        harmony = harmony_score(palette)
        avg_l = sum(hex_to_hsl(c)[2] for c in palette) / max(len(palette), 1)
        palette_formality = 1 + (len(neutrals) / max(len(palette), 1)) * 1.2 + (0.7 if avg_l < 45 else 0)
        target = OCCASION_FORMALITY.get(ctx.occasion, 1.8)
        occasion_fit = _clamp(92 - abs(palette_formality - target) * 11 + (seed % 7), 62, 95)

        temp = ctx.weather.tempC
        warm_day, cool_day, light = temp >= 24, temp <= 13, avg_l >= 58
        comfort = 80
        if warm_day and light:
            comfort = 90
        if warm_day and avg_l < 40:
            comfort = 70
        if cool_day and avg_l < 50:
            comfort = 87
        comfort = _clamp(comfort + (seed % 5), 62, 95)

        cohesion = _clamp(
            72 + (10 if 2 <= len(palette) <= 4 else 0) + min(len(neutrals), 2) * 5 + (seed % 6),
            62, 95,
        )
        score = _clamp(harmony * 0.38 + occasion_fit * 0.24 + comfort * 0.16 + cohesion * 0.22, 62, 96)

        what_works: list[str] = []
        if len(colored) >= 2:
            what_works.append(
                f"The {color_name(colored[0])} and {color_name(colored[1])} sit beautifully together — that pairing is doing real work."
            )
        elif len(colored) == 1:
            what_works.append(
                f"Letting {color_name(colored[0])} carry the look keeps everything focused and intentional."
            )
        else:
            what_works.append(
                f"A fully neutral palette — {' and '.join(names[:2])} — always reads calm and expensive."
            )
        if len(neutrals) >= 1 and len(colored) >= 1:
            what_works.append(
                f"Your {color_name(neutrals[0])} grounds the colour so nothing fights for attention."
            )
        if occasion_fit >= 80:
            what_works.append(f"The overall mood fits {_occasion_label(ctx.occasion)} naturally.")

        weakest = min(harmony, occasion_fit, comfort)
        if weakest == harmony and len(colored) >= 2:
            gentle = (
                f"If you ever want a softer blend, swapping one piece toward "
                f"{_pick(['ivory', 'taupe', 'blush'], seed)} would let the {color_name(colored[0])} breathe a little more."
            )
        elif weakest == comfort and warm_day:
            gentle = f"It's {round(temp)}° today — a lighter layer would keep this look feeling effortless all day."
        elif weakest == comfort and cool_day:
            gentle = f"At {round(temp)}°, tossing a warm layer over this keeps the silhouette and adds coziness."
        elif weakest == occasion_fit:
            gentle = (
                f"For {_occasion_label(ctx.occasion)}, one slightly dressier piece — shoes or a structured layer — would lift it perfectly."
                if target >= 2.2
                else f"This leans a touch polished for {_occasion_label(ctx.occasion)} — which honestly is never a bad thing."
            )
        else:
            gentle = "Honestly? I wouldn't change a thing. Maybe one small accent if you're feeling playful."

        aura = _pick(
            [
                f"You wanted to feel {ctx.profile.feeling} today — this gets you there, {ctx.profile.name}.",
                f"{ctx.profile.name}, you wear this like it was made for you.",
                f"Walk out the door, {ctx.profile.name}. You're ready.",
                f"Soft, certain, and very you, {ctx.profile.name}.",
            ],
            seed,
        )

        return Judgment(
            score=score,
            headline=_pick(HEADLINES_HIGH, seed) if score >= 84 else _pick(HEADLINES_MID, seed),
            harmony=harmony,
            occasion_fit=occasion_fit,
            comfort=comfort,
            cohesion=cohesion,
            what_works=what_works[:3],
            gentle_thought=gentle,
            aura_note=aura,
        )


class QwenAnalyzer:
    """Planned default (Qwen2.5-VL). Not wired — this IS the swap point."""

    def __init__(self, framework_text: str, model: str) -> None:
        self.framework = framework_text
        self.model = model

    def _unwired(self):
        raise NotImplementedError(
            f"{self.model} is not wired yet. This is the swappable boundary: load the "
            "VLM, feed it the framework + isolated garment crop, and return the same "
            "Perception/Judgment contract. See architecture-decisions.md."
        )

    def perceive(self, palette: list[str]) -> Perception:  # pragma: no cover
        self._unwired()

    def judge(self, perception: Perception, palette: list[str], ctx: AnalyzeRequest) -> Judgment:  # pragma: no cover
        self._unwired()


def get_analyzer() -> Analyzer:
    framework = load_framework()
    model = config.MODEL
    if model == "honest-mock":
        return HonestMockAnalyzer(framework)
    if model.startswith("qwen"):
        return QwenAnalyzer(framework, model)
    raise ValueError(f"Unknown LOVANYA_MODEL={model!r} (expected 'honest-mock' or 'qwen...').")
