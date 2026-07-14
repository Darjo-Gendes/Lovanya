"""Generation-QA confidence — the image-grounded signal.

Qwen3-VL looks at each generated product shot next to the ORIGINAL photo and
the intended description, and scores how faithfully the render represents the
garment (type / color / shape). This is the signal perception confidence
can't give: it catches a render that disagrees with a CORRECT description —
e.g. a "true black" top rendered olive-green (the user's #1 recurring
complaint, flagged on sample_r4c4 and sample_r4c5).

Scores land in review/garments_omini/qa.json keyed by shot id; the rating
page reads them and sorts low-confidence items to the top.

Usage:
  python pipeline/scripts/score_generation.py            # all shots
  python pipeline/scripts/score_generation.py b2_r1c4    # one stem
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from local_describe import ask, parse_object  # reuse the Qwen3-VL loader  # noqa: E402

SHOTS = ROOT / "review" / "garments_omini" / "shots"
SAMPLES = ROOT / "samples"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
QA_OUT = ROOT / "review" / "garments_omini" / "qa.json"


def _strip_hex(s: str) -> str:
    return re.sub(r"\s*\(?~?#?[0-9a-fA-F]{6}\)?", "", str(s)).replace("()", "").strip()


JUDGE_TEMPLATE = """You are a strict e-commerce QA reviewer.
IMAGE 1 is an AI-generated product shot of a single garment on a white background.
IMAGE 2 is the ORIGINAL outfit photo the garment was extracted from (find the {category} in it).

The product shot was meant to represent: a {archetype} ({item}), stated color "{color}".
Full intended description: {prompt}

Judge how faithfully IMAGE 1 represents that real garment. Be strict and literal:
- type_match: is it the right KIND of garment (e.g. hoodie vs tee, blazer vs cardigan, box-flap bag vs tote)? 0.0-1.0
- color_match: does IMAGE 1's color match the stated color AND the garment's true color in IMAGE 2? A clearly different hue (e.g. black rendered as olive or navy) is a hard fail near 0.0. 0.0-1.0
- shape_match: silhouette, proportions, key details (collar, sleeves, hardware) correct? 0.0-1.0
- overall: your single 0.0-1.0 confidence that this product shot is a faithful, sellable representation.
- issues: a SHORT list of concrete problems (especially any color mismatch), or "none".

Return ONLY a JSON object:
{{"type_match": 0.0, "color_match": 0.0, "shape_match": 0.0, "overall": 0.0, "issues": "..."}}"""


def score_shot(shot: Path, g: dict, src: Path) -> dict:
    prompt = JUDGE_TEMPLATE.format(
        category=g.get("category", "garment"),
        archetype=g.get("archetype", g.get("item", "garment")),
        item=g.get("item", ""),
        color=_strip_hex(g.get("color", "")),
        prompt=_strip_hex(g.get("prompt", ""))[:220],
    )
    raw = ask([str(shot), str(src)], prompt, max_new_tokens=300)
    rec = parse_object(raw)
    for k in ("type_match", "color_match", "shape_match", "overall"):
        try:
            rec[k] = round(float(rec.get(k, 0)), 2)
        except (TypeError, ValueError):
            rec[k] = 0.0
    rec["band"] = ("high" if rec["overall"] >= 0.7
                   else "medium" if rec["overall"] >= 0.45 else "low")
    return rec


def stem_of(shot: Path) -> tuple[str, int]:
    parts = shot.stem.rsplit("_", 2)
    return parts[0], int(parts[1])


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shots = sorted(SHOTS.glob("*.png"))
    if args:
        shots = [s for s in shots if stem_of(s)[0] in args]
    qa = json.loads(QA_OUT.read_text(encoding="utf-8")) if QA_OUT.exists() else {}

    desc_cache: dict[str, list] = {}
    done = 0
    for shot in shots:
        stem, idx = stem_of(shot)
        if stem not in desc_cache:
            f = DESCS / f"{stem}.json"
            desc_cache[stem] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        garments = desc_cache[stem]
        if idx >= len(garments):
            continue
        g = garments[idx]
        src = SAMPLES / f"{stem}.jpg"
        t = time.time()
        rec = score_shot(shot, g, src)
        qa[shot.stem] = rec
        done += 1
        print(f"  [{done}/{len(shots)}] {shot.stem}: overall {rec['overall']} ({rec['band']}) "
              f"color {rec['color_match']} | {str(rec.get('issues',''))[:60]} ({time.time()-t:.0f}s)",
              flush=True)
        QA_OUT.write_text(json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"QA DONE: {done} shots scored -> {QA_OUT}", flush=True)


if __name__ == "__main__":
    main()
