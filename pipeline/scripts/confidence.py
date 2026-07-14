"""Confidence scoring for the garment pipeline — two independent signals.

PERCEPTION confidence (this module, deterministic, no GPU): how much evidence
did the vision model actually have? Driven by crop size (a 30px bag is a
guess), occlusion, and how many attributes came back "not visible/unclear".
Validated intent: the user flagged "low confidence" exactly on tiny/occluded
items (small bag crops, trousers hidden below the waist).

GENERATION-QA confidence lives in score_generation.py (needs the VLM to look
at the render). Kept separate because it catches a different failure — the
render disagreeing with a CORRECT description (true-black top rendered olive).

Both are surfaced in rate.html so thin-evidence items sort to the top.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
SAMPLES = ROOT / "samples"

_UNKNOWN_MARKERS = ("not visible", "unclear", "inferred", "unknown", "n/a", "not applicable")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def bbox_area_fraction(bbox, img_w: int, img_h: int) -> float:
    """Fraction of the image the garment box covers, handling both pixel and
    0-1000-normalized coordinate spaces (Qwen3-VL grounding emits normalized)."""
    try:
        x1, y1, x2, y2 = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return 0.0
    if max(x1, y1, x2, y2) > max(img_w, img_h) + 2:      # normalized 0-1000
        area = abs(x2 - x1) * abs(y2 - y1) / (1000.0 * 1000.0)
    else:
        area = abs(x2 - x1) * abs(y2 - y1) / float(max(1, img_w * img_h))
    return _clamp(area)


def perception_confidence(g: dict, img_w: int, img_h: int) -> dict:
    """-> {score 0-1, band, reasons[]}. Deterministic from the description JSON."""
    reasons = []

    # 1. crop size — the dominant signal for these thumbnails. ~6% of the frame
    # is a comfortably-resolved garment; below that, detail is a guess.
    frac = bbox_area_fraction(g.get("bbox"), img_w, img_h)
    size_score = _clamp(frac / 0.06)
    if size_score < 0.5:
        reasons.append(f"small crop ({frac*100:.1f}% of frame)")

    # 2. occlusion — a hidden garment is inferred, not seen
    occ = str(g.get("occluded", "no")).lower()
    occluded = occ not in ("no", "", "none")
    occ_score = 0.55 if occluded else 1.0
    if occluded:
        reasons.append(f"occluded ({occ})")

    # 3. attribute completeness — many "not visible" = the model filled gaps
    attrs = g.get("attributes", {})
    vals = [str(v).lower() for v in attrs.values()] if isinstance(attrs, dict) else []
    unknown = sum(1 for v in vals if any(m in v for m in _UNKNOWN_MARKERS))
    comp_score = _clamp(1.0 - 0.12 * unknown, 0.3, 1.0)
    if unknown >= 3:
        reasons.append(f"{unknown} attributes not visible")

    score = round(0.5 * size_score + 0.25 * occ_score + 0.25 * comp_score, 2)
    band = "high" if score >= 0.7 else ("medium" if score >= 0.45 else "low")
    if not reasons:
        reasons.append("clear, well-sized crop")
    return {"score": score, "band": band, "reasons": reasons,
            "signals": {"size": round(size_score, 2), "occlusion": round(occ_score, 2),
                        "completeness": round(comp_score, 2)}}


def _parse_hex(color: str):
    m = re.search(r"#([0-9a-fA-F]{6})", str(color))
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return None


def generation_color_delta(shot_path, intended_color: str) -> dict | None:
    """Sample the garment's dominant color in the product shot and detect a
    render-vs-spec color failure. HEX-ONLY (no vague-name guessing).

    Two regimes, because Euclidean RGB conflates hue error with lightness:
    - intended is DARK/NEUTRAL (black, dark grey): the failure is a color CAST
      appearing where none should be (black -> olive/navy). Flag on the
      render's RELATIVE chroma, which is lightness-invariant.
    - intended is LIGHT/COLORED: hex is approximate, so only a GROSS Euclidean
      error is a real mismatch (avoids flagging acceptable cream/beige drift).
    A flag surfaces the item for review, it does not reject it. -> dict | None."""
    import numpy as np
    from PIL import Image

    # multi-color / patterned items have no single dominant color -> skip
    c = str(intended_color).lower()
    if len(re.findall(r"#[0-9a-fA-F]{6}", c)) >= 2 or any(
            k in c for k in ("stripe", "plaid", "check", "floral", "pattern", "print", " and ")):
        return None
    intended = _parse_hex(intended_color)
    if intended is None:
        return None
    im = Image.open(shot_path).convert("RGB")
    a = np.asarray(im).reshape(-1, 3).astype(np.float32)
    nonbg = a[(a.min(axis=1) < 232) | (a.max(axis=1) - a.min(axis=1) > 18)]
    if len(nonbg) < 50:
        return None
    rendered = tuple(int(v) for v in np.median(nonbg, axis=0))
    delta = float(np.sqrt(sum((rendered[i] - intended[i]) ** 2 for i in range(3))))

    intended_chroma = max(intended) - min(intended)
    dark_neutral = intended_chroma < 40 and max(intended) < 120
    if dark_neutral:
        rel_chroma = (max(rendered) - min(rendered)) / (max(rendered) + 1)
        mismatch = rel_chroma > 0.20
        reason = f"dark garment rendered with a color cast (rel-chroma {rel_chroma:.2f})" if mismatch else ""
    else:
        mismatch = delta > 130
        reason = f"color far from spec (delta {delta:.0f})" if mismatch else ""
    return {"delta": round(delta, 1), "rendered_rgb": rendered,
            "intended_rgb": intended, "mismatch": mismatch, "reason": reason}


SHOTS = ROOT / "review" / "garments_omini" / "shots"


def combine(perception: dict, color: dict | None) -> dict:
    """Merge the two signals into one review verdict. A hard color mismatch
    dominates (it's a confirmed render defect); otherwise perception drives."""
    flags = []
    if color and color.get("mismatch"):
        flags.append("color: " + color.get("reason", "render color off"))
    if perception["band"] == "low":
        flags.append("perception: " + "; ".join(perception["reasons"]))
    if color and color.get("mismatch"):
        band, score = "low", min(perception["score"], 0.35)
    else:
        band, score = perception["band"], perception["score"]
    return {"review_band": band, "review_score": score,
            "flags": flags or ["no automatic flags"]}


def backfill(stems: list[str] | None = None) -> None:
    """Add perception_confidence + generation_color + combined review verdict to
    every garment. Idempotent. Writes a flat confidence.json sidecar too, keyed
    by shot id, for the rating page to read."""
    from PIL import Image
    files = ([DESCS / f"{s}.json" for s in stems] if stems
             else sorted(DESCS.glob("*.json")))
    sidecar_path = SHOTS.parent / "confidence.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8")) if sidecar_path.exists() else {}
    n = 0
    for f in files:
        if not f.exists() or f.name.endswith(".v1.json"):
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        src = SAMPLES / f"{f.stem}.jpg"
        if not src.exists():
            continue
        w, h = Image.open(src).size
        for i, g in enumerate(data):
            if g.get("_parse_error"):
                continue
            pc = perception_confidence(g, w, h)
            shot = next(SHOTS.glob(f"{f.stem}_{i}_*.png"), None)
            cc = generation_color_delta(shot, g.get("color", "")) if shot else None
            verdict = combine(pc, cc)
            g["perception_confidence"] = pc
            g["generation_color"] = cc
            g["review"] = verdict
            if shot:
                sidecar[shot.stem] = {"perception": pc, "color": cc, **verdict}
            n += 1
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"backfilled confidence for {n} garments; sidecar -> {sidecar_path}")


if __name__ == "__main__":
    backfill([a for a in sys.argv[1:] if not a.startswith("--")] or None)
