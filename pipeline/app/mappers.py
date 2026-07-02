"""Map the analyzer's internal outputs to (a) the canonical contract for logging
and (b) the app-facing shapes the Next.js frontend already understands.
"""
from __future__ import annotations

from .color import color_name, is_neutral
from .contracts import (
    AnalyzeRequest,
    Breakdown,
    DimensionScores,
    Garment,
    ItemDraftOut,
    Judgment,
    OutfitAnalysisOut,
    Perception,
    Verdict,
)

_FIT_BY_FORMALITY = {1: "loose", 2: "regular", 3: "fitted"}


def _main_color(colors: list[str]) -> str:
    return next((c for c in colors if not is_neutral(c)), colors[0] if colors else "#b8a8b0")


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


# ---- canonical contract (swappable-boundary shape, logged on every call) ------
def garment_from(p: Perception) -> Garment:
    colors = p.colors or []
    return Garment(
        category=p.category,
        subcategory=p.subcategory,
        color_primary=color_name(_main_color(colors)),
        color_secondary=color_name(colors[1]) if len(colors) > 1 else "",
        pattern="solid",
        formality={1: "casual", 2: "smart-casual", 3: "business"}.get(p.formality, "casual"),  # type: ignore[arg-type]
        fit=_FIT_BY_FORMALITY.get(p.warmth, "regular"),  # type: ignore[arg-type]
        season="all",
        notes=p.subcategory,
    )


def verdict_from(j: Judgment, palette: list[str]) -> Verdict:
    # Derive the 6 brand dimensions from the grounded sub-scores. (The framework
    # leaves exact definitions as TODO; these are honest, reproducible defaults.)
    dims = DimensionScores(
        color_harmony=j.harmony,
        elegance=_clamp(round(0.6 * j.cohesion + 0.4 * j.occasion_fit), 55, 96),
        outfit_cohesion=j.cohesion,
        confidence_boost=_clamp(round((j.score + j.occasion_fit) / 2), 60, 96),
        consistency=_clamp(round((j.harmony + j.cohesion) / 2), 60, 96),
        style_growth=_clamp(round(0.5 * j.score + 30), 58, 92),
    )
    return Verdict(
        dimension_scores=dims,
        editorial_read=f"{j.headline}. {j.what_works[0]}" if j.what_works else j.headline,
        elevate_suggestions=[j.gentle_thought],
    )


# ---- app-facing shapes (mirror lovanya/lib/types.ts) -------------------------
def to_item_draft(p: Perception, modest: bool) -> ItemDraftOut:
    main = _main_color(p.colors)
    return ItemDraftOut(
        name=f"{_cap(color_name(main))} {p.subcategory}".strip(),
        category=p.category,
        colors=p.colors[:3],
        warmth=p.warmth,
        formality=p.formality,
        modest=modest,
    )


def to_outfit_analysis(j: Judgment, palette: list[str], ctx: AnalyzeRequest) -> OutfitAnalysisOut:
    return OutfitAnalysisOut(
        score=j.score,
        headline=j.headline,
        palette=palette,
        paletteNames=[color_name(c) for c in palette],
        breakdown=[
            Breakdown(label="Color harmony", score=j.harmony,
                      note="Beautifully balanced" if j.harmony >= 82 else "Gentle and workable"),
            Breakdown(label="Occasion fit", score=j.occasion_fit,
                      note="Right at home" if j.occasion_fit >= 80 else "Close — one tweak"),
            Breakdown(label="Weather comfort", score=j.comfort,
                      note=f"{round(ctx.weather.tempC)}° · {ctx.weather.label}".strip(" ·")),
            Breakdown(label="Cohesion", score=j.cohesion,
                      note="Everything belongs" if j.cohesion >= 82 else "Nearly seamless"),
        ],
        whatWorks=j.what_works,
        gentleThought=j.gentle_thought,
        auraNote=j.aura_note,
    )


def _clamp(v: float, lo: int, hi: int) -> int:
    return round(max(lo, min(hi, v)))
