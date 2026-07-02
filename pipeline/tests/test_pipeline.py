"""End-to-end smoke tests — the pipeline runs and honours the contracts with no
GPU. Run from the repo root:  pytest
"""
from __future__ import annotations

import pytest

from pipeline.app.analyze import get_analyzer
from pipeline.app.contracts import AnalyzeRequest, ProfileIn, WeatherIn
from pipeline.app.mappers import garment_from, verdict_from
from pipeline.app.pipeline import PipelineError, run_analyze, run_identify

PALETTE = ["#e5d2c0", "#9caac4", "#262521"]
CATEGORIES = {"top", "bottom", "dress", "outerwear", "shoes", "bag", "accessory"}


def test_identify_returns_valid_draft():
    d = run_identify(None, PALETTE, modest_default=True)
    assert d.category in CATEGORIES
    assert d.name and d.colors
    assert d.modest is True
    assert d.warmth in (1, 2, 3) and d.formality in (1, 2, 3)


def test_analyze_returns_scored_analysis():
    ctx = AnalyzeRequest(
        palette=PALETTE,
        occasion="work",
        weather=WeatherIn(tempC=22, label="Cloudy"),
        profile=ProfileIn(name="Sarah", feeling="calm"),
    )
    a = run_analyze(None, PALETTE, ctx)
    assert 62 <= a.score <= 96
    assert len(a.breakdown) == 4
    assert all(55 <= b.score <= 96 for b in a.breakdown)  # harmony clamps to [55, 96]
    assert a.whatWorks and a.gentleThought and a.auraNote
    assert len(a.paletteNames) == 3 and all(a.paletteNames)  # grounded colour naming


def test_canonical_contract_shape():
    analyzer = get_analyzer()
    p = analyzer.perceive(PALETTE)
    j = analyzer.judge(p, PALETTE, AnalyzeRequest(palette=PALETTE))
    garment = garment_from(p)
    verdict = verdict_from(j, PALETTE)
    # all six brand dimensions present and in range
    dims = verdict.dimension_scores.model_dump()
    assert set(dims) == {
        "color_harmony", "elegance", "outfit_cohesion",
        "confidence_boost", "consistency", "style_growth",
    }
    assert all(0 <= v <= 100 for v in dims.values())
    assert garment.color_primary and verdict.elevate_suggestions


def test_empty_palette_raises():
    with pytest.raises(PipelineError):
        run_identify(None, [], modest_default=False)
    with pytest.raises(PipelineError):
        run_analyze(None, [], AnalyzeRequest())


def test_determinism():
    a1 = run_analyze(None, PALETTE, AnalyzeRequest(palette=PALETTE, occasion="date"))
    a2 = run_analyze(None, PALETTE, AnalyzeRequest(palette=PALETTE, occasion="date"))
    assert a1.score == a2.score and a1.headline == a2.headline
