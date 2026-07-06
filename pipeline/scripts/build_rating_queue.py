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
    args = parser.parse_args()

    queue = reuse_from_log()
    print(f"reused {len(queue)} pre-computed judgments", flush=True)

    if args.target and len(queue) < args.target:
        from pipeline.app.analyze import analyze
        samples = sorted((PIPELINE / "samples").glob("*.jpg"))
        # spread across occasions for a useful rating set
        occasions = ["casual", "work", "date night", "party", "brunch",
                     "interview", "wedding", "kondangan"]
        need = args.target - len(queue)
        picked = [p for p in samples if p.name not in queue][:need]
        for i, p in enumerate(picked):
            occ = occasions[i % len(occasions)]
            print(f"  generating {p.name} / {occ} ({i+1}/{len(picked)})…", flush=True)
            r = analyze(str(p), occ)
            queue[p.name] = {
                "image": p.name, "occasion": occ,
                "judgment_id": r.get("judgment_id", p.name),
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
