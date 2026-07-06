"""Sanity-check that the active judge still scores outfit/occasion MISMATCHES
low (the discrimination the outlier gold examples were meant to teach).

Loads the model once, runs a few deliberately-wrong pairings, prints compact
results. Run from the repo root:  python pipeline/scripts/check_outliers.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline import config  # noqa: E402
from pipeline.app.analyze import analyze  # noqa: E402

# (image, occasion, gold_overall) — all deliberate mismatches, gold-scored low
OUTLIERS = [
    ("samples/b4_r5c6.jpg", "wedding", 3),          # leopard cami + floral sarong
    ("samples/b2_r5c1.jpg", "belanja ke pasar", 4), # neon colorblock + leopard pants
    ("samples/b4_r5c5.jpg", "interview", 3),        # pink blazer + graphic tee + neon pants
]

PIPELINE_DIR = Path(__file__).resolve().parent.parent


def main():
    from pipeline.app.qwen_analyzer import resolve_adapter

    print(f"adapter: {resolve_adapter(config.ADAPTER) or 'base model'}", flush=True)
    for image, occasion, gold in OUTLIERS:
        r = analyze(str(PIPELINE_DIR / image), occasion)
        j = r["judgment"]
        print(json.dumps({
            "image": image,
            "occasion": occasion,
            "gold_overall": gold,
            "model_overall": j.get("overall"),
            "occasion_fit": j.get("scores", {}).get("occasion_fit"),
            "feedback": j.get("feedback"),
            "one_fix": j.get("one_fix"),
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
