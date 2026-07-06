"""Build data/rating-queue.jsonl — the queue the /rate page serves so you can
rate the model's judgments instantly (no GPU wait per card).

Two sources:
  1. reuse: every already-computed judgment in logs/judgments.jsonl (instant);
  2. generate: run the current model on more samples to reach --target
     (GPU, ~5 min each) — only for samples not already in the queue.

Run from the repo root:
    python pipeline/scripts/build_rating_queue.py                 # reuse only
    python pipeline/scripts/build_rating_queue.py --target 20     # + generate
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

PIPELINE = Path(__file__).resolve().parent.parent
QUEUE = PIPELINE / "data" / "rating-queue.jsonl"
LOG = PIPELINE / "logs" / "judgments.jsonl"

# Edge-case-weighted rating set: teach the model where the lines are. Heavy on
# deliberate outfit/occasion MISMATCHES (loud outfits at formal occasions),
# plus good outfits so the high end is confirmed, not lost.
CURATED_PAIRS = [
    # clear mismatches — loud / casual outfit at a formal or wrong occasion
    ("samples/b2_r5c2.jpg", "kondangan"),      # band tee + patchwork pants
    ("samples/b2_r5c3.jpg", "interview"),      # orange loud-print + printed hijab
    ("samples/b2_r5c4.jpg", "pengajian"),      # tie-dye + printed pants + bucket hat
    ("samples/b4_r5c1.jpg", "wedding"),        # rainbow tie-dye + neon shorts
    ("samples/b4_r5c2.jpg", "ngantor"),        # pastel cartoon PJ-style set at office
    ("samples/b4_r5c3.jpg", "interview"),      # neon mesh over pink
    ("samples/b4_r5c4.jpg", "kondangan"),      # cartoon tee + printed shorts
    ("samples/sample_r3c5.jpg", "ngantor"),    # pink paisley maximalism at office
    # borderline — casual/wrong-register at a semi-formal or wrong occasion
    ("samples/sample_r1c2.jpg", "wedding"),    # black knit + jeans, too casual
    ("samples/b3_r1c3.jpg", "ngantor"),        # gym sports bra + leggings at office
    ("samples/b2_r1c3.jpg", "kondangan"),      # gym kit at a formal wedding
    ("samples/b4_r1c3.jpg", "interview"),      # striped cardigan + jeans, too casual
    # good — nice outfit at the right occasion; the high end must survive
    ("samples/sample_r1c5.jpg", "date night"), # cream puff-sleeve dress
    ("samples/sample_r2c1.jpg", "work"),       # olive blazer + white + jeans
    ("samples/b2_r1c1.jpg", "kondangan"),      # black lace kebaya + batik
    ("samples/b2_r2c2.jpg", "pengajian"),      # blush hijab + gamis
    ("samples/b3_r2c1.jpg", "kondangan"),      # sage kebaya + brooch + batik
    ("samples/b4_r2c3.jpg", "presentation"),   # beige vest suit
    ("samples/b3_r1c4.jpg", "kuliah"),         # layered hijab campus look
    ("samples/b2_r4c1.jpg", "arisan"),         # green blouse + batik
]


def reuse_from_log() -> dict:
    """image basename -> queue record, from logged bench judgments (latest wins)."""
    out = {}
    if not LOG.exists():
        return out
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("kind") != "analyze-bench":
            continue
        inp, o = r.get("input", {}), r.get("output", {})
        j, img = o.get("judgment", {}), inp.get("image_path", "")
        if not img or not isinstance(j, dict) or "overall" not in j:
            continue
        name = os.path.basename(img)
        out[name] = {
            "image": name,
            "occasion": inp.get("occasion"),
            "judgment_id": inp.get("judgment_id") or name,
            "perception": o.get("perception", {}),
            "judgment": j,
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=0,
                        help="generate more (GPU) until the queue has this many")
    parser.add_argument("--curated", action="store_true",
                        help="generate the edge-case-weighted CURATED_PAIRS set (GPU)")
    args = parser.parse_args()

    queue = reuse_from_log()
    print(f"reused {len(queue)} pre-computed judgments", flush=True)

    if args.curated or (args.target and len(queue) < args.target):
        from pipeline.app.analyze import analyze
        if args.curated:
            # (image, occasion) pairs keyed so re-runs skip what's done
            todo = [(p, o) for p, o in CURATED_PAIRS
                    if f"{Path(p).stem}|{o}" not in queue and Path(p).name not in queue]
        else:
            samples = sorted((PIPELINE / "samples").glob("*.jpg"))
            occasions = ["casual", "work", "date night", "party", "brunch",
                         "interview", "wedding", "kondangan"]
            need = args.target - len(queue)
            todo = [(str(p), occasions[i % len(occasions)])
                    for i, p in enumerate(p for p in samples if p.name not in queue)][:need]
        for i, (img, occ) in enumerate(todo):
            print(f"  generating {Path(img).name} / {occ} ({i+1}/{len(todo)})…", flush=True)
            r = analyze(str(PIPELINE / img) if not Path(img).is_absolute() else img, occ)
            # key by image|occasion so the same photo can appear at 2 occasions
            key = f"{Path(img).stem}|{occ}"
            queue[key] = {
                "image": Path(img).name, "occasion": occ,
                "judgment_id": r.get("judgment_id", key),
                "perception": r.get("perception", {}), "judgment": r.get("judgment", {}),
            }

    QUEUE.parent.mkdir(exist_ok=True)
    QUEUE.write_text(
        "\n".join(json.dumps(v, ensure_ascii=False) for v in queue.values()),
        encoding="utf-8",
    )
    print(f"wrote {len(queue)} records to {QUEUE}", flush=True)


if __name__ == "__main__":
    main()
