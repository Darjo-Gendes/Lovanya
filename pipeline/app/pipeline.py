"""The linear, bounded orchestrator: photo|palette -> segment -> analyze ->
render -> result. No branching, no conversation — one shot, per
architecture-decisions.md (#3 structured one-shot inference).
"""
from __future__ import annotations

from typing import Optional

from .. import config
from .analyze import get_analyzer
from .color import extract_palette
from .contracts import AnalyzeRequest, Analysis, ItemDraftOut, OutfitAnalysisOut
from .logging_store import log_judgment
from .mappers import garment_from, to_item_draft, to_outfit_analysis, verdict_from
from .render import render
from .segment import segment


class PipelineError(ValueError):
    """A request that cannot be processed (no garment / empty palette)."""


def _resolve_palette(palette: Optional[list[str]], image: Optional[bytes]) -> list[str]:
    region = segment(image)
    if palette:
        return [c for c in palette if isinstance(c, str) and c]
    if region.detected and region.crop is not None:
        return extract_palette(region.crop, count=4)
    return []


def run_identify(image: Optional[bytes], palette: Optional[list[str]], modest_default: bool) -> ItemDraftOut:
    pal = _resolve_palette(palette, image)
    if not pal:
        raise PipelineError("No garment detected and no palette provided.")
    perception = get_analyzer().perceive(pal)
    draft = to_item_draft(perception, modest_default)
    log_judgment("identify", config.MODEL, {"palette": pal}, garment_from(perception))
    return draft


def run_analyze(image: Optional[bytes], palette: Optional[list[str]], ctx: AnalyzeRequest) -> OutfitAnalysisOut:
    pal = _resolve_palette(palette, image)
    if not pal:
        raise PipelineError("No outfit detected and no palette provided.")
    analyzer = get_analyzer()
    perception = analyzer.perceive(pal)
    judgment = analyzer.judge(perception, pal, ctx)
    render(segment(image).crop)  # optional clean shot (stubbed)

    canonical = Analysis(garment=garment_from(perception), verdict=verdict_from(judgment, pal))
    log_judgment("analyze", config.MODEL, ctx.model_dump(), canonical)
    return to_outfit_analysis(judgment, pal, ctx)
