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


def test_palette_suppresses_background():
    """A beige wall behind a navy dress must not enter the palette
    (visual-pipeline-v1 interim fix; the real fix is SAM2 cutouts)."""
    import io

    from PIL import Image

    from pipeline.app.color import extract_palette, hex_to_rgb

    wall = (222, 205, 190)  # beige background fills the frame
    img = Image.new("RGB", (200, 200), wall)
    for x in range(60, 140):  # navy dress, center-frame
        for y in range(30, 185):
            img.putpixel((x, y), (30, 45, 90))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    palette = extract_palette(buf.getvalue(), 4)
    assert palette, "palette must never be empty"

    # The garment leads the palette…
    r, g, b = hex_to_rgb(palette[0])
    assert b > r, f"expected navy first, got {palette[0]}"
    # …and nothing background-like survives.
    for hexstr in palette:
        r, g, b = hex_to_rgb(hexstr)
        dist = abs(r - wall[0]) + abs(g - wall[1]) + abs(b - wall[2])
        assert dist > 75, f"background leaked into palette: {hexstr}"


def test_palette_uniform_scene_still_works():
    """Safety floor: garment the same color as the wall must not empty the palette."""
    import io

    from PIL import Image

    from pipeline.app.color import extract_palette

    img = Image.new("RGB", (200, 200), (230, 225, 218))  # cream on cream
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    palette = extract_palette(buf.getvalue(), 4)
    assert len(palette) >= 1
