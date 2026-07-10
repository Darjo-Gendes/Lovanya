"""AFK phase 1 — detect + SAM2 cutout garments from 20 random samples.

Writes cutout PNGs + review/garments/manifest.jsonl. Runs as its own process
so GroundingDINO + SAM2 are freed before the SDXL shot phase (8GB guardrail).
"""
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

import extract_garments as eg  # noqa: E402
from pipeline.app.cutout import sam2_cutout  # noqa: E402

PIPELINE = Path(__file__).resolve().parent.parent
SAMPLES = PIPELINE / "samples"
OUT = PIPELINE / "review" / "garments"
CUTS = OUT / "cutouts"

N_SAMPLES = 20
MAX_PER_SAMPLE = 5

CAT_NOUN = {"top": "long-sleeve top", "bottom": "wide-leg trousers", "dress": "dress",
            "outerwear": "shirt jacket", "shoes": "shoes", "bag": "handbag", "accessory": "accessory"}
BASIC = {"black": (20, 20, 20), "white": (238, 238, 238), "grey": (128, 128, 128),
         "navy": (30, 40, 80), "blue": (60, 110, 200), "red": (200, 50, 50),
         "pink": (233, 130, 168), "green": (110, 150, 95), "beige": (215, 195, 165),
         "brown": (120, 85, 60), "cream": (240, 230, 205), "sage": (150, 165, 120)}


def color_name(rgba):
    import numpy as np
    a = np.asarray(rgba.convert("RGBA")); m = a[..., 3] > 40
    if m.sum() == 0:
        return ""
    px = a[m][:, :3].mean(axis=0); r, g, b = px
    if min(r, g, b) > 200 and (max(r, g, b) - min(r, g, b)) < 22:
        return "white"
    return min(BASIC, key=lambda k: sum((px[i] - BASIC[k][i]) ** 2 for i in range(3)))


def guard(dets, W, H):
    """drop whole-body boxes, phone false-positives, whole-outfit containers."""
    area = W * H
    def ba(b): return (b[2] - b[0]) * (b[3] - b[1])
    def ctr(b): return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    def has(o, p): return o[0] <= p[0] <= o[2] and o[1] <= p[1] <= o[3]
    out = []
    for d in dets:
        if ba(d["box"]) > 0.60 * area:
            continue
        if ba(d["box"]) > 0.42 * area and sum(1 for x in dets if x is not d and has(d["box"], ctr(x["box"]))) >= 2:
            continue
        if d["cat"] in ("bag", "accessory") and d["score"] < 0.45:
            continue
        out.append(d)
    return out[:MAX_PER_SAMPLE]


def main():
    CUTS.mkdir(parents=True, exist_ok=True)
    import torch
    from transformers import pipeline
    eg._detector = pipeline("zero-shot-object-detection",
                            model="IDEA-Research/grounding-dino-tiny",
                            device=0 if torch.cuda.is_available() else -1)

    random.seed(20)
    pool = sorted(SAMPLES.glob("*.jpg"))
    picks = random.sample(pool, min(N_SAMPLES, len(pool)))
    manifest = []
    for n, p in enumerate(picks, 1):
        pil = Image.open(p).convert("RGB")
        dets = guard(eg.dedup(eg.detect(pil)), pil.width, pil.height)
        for i, d in enumerate(dets):
            cut = sam2_cutout(pil, d["box"])
            path = CUTS / f"{p.stem}_{i}_{d['cat']}.png"
            cut.save(path)
            manifest.append({"sample": p.name, "cutout": str(path), "cat": d["cat"],
                             "garment": CAT_NOUN.get(d["cat"], d["label"]),
                             "color": color_name(cut)})
        print(f"[{n}/{len(picks)}] {p.name}: {len(dets)} garments", flush=True)

    (OUT / "manifest.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in manifest), encoding="utf-8")
    print(f"CUT PHASE DONE: {len(manifest)} cutouts from {len(picks)} samples", flush=True)


if __name__ == "__main__":
    main()
