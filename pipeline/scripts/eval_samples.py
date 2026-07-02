"""Run a fixed evaluation set through the pipeline and write a markdown report.

Usage (from pipeline/):
    python scripts/eval_samples.py [--out EVAL-REPORT.md]

Used to eyeball judgment quality after model or framework changes, and as a
manual regression check before/after fine-tuning.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.analyze import analyze  # noqa: E402

# Chosen to cover the judgment rules: modest dress (r5c2, r5c3), garment-swap
# phrasing (r4c4), print-on-print (r3c3), simple strong outfits (r1c1, r4c5),
# occasion discipline (r2c6 formal-ish dress judged for brunch).
EVAL_SET = [
    ("samples/sample_r1c1.jpg", "casual"),
    ("samples/sample_r3c3.jpg", "party"),
    ("samples/sample_r4c4.jpg", "casual"),
    ("samples/sample_r5c2.jpg", "work"),
    ("samples/sample_r5c3.jpg", "work"),
    ("samples/sample_r2c6.jpg", "weekend brunch"),
    ("samples/sample_r4c5.jpg", "casual"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="EVAL-REPORT.md")
    args = parser.parse_args()

    lines = [
        "# Judgment evaluation report",
        "",
        f"- model: `{config.QWEN_MODEL_ID}` (QUANT={config.QUANT}, SEGMENT={config.SEGMENT})",
        f"- generated: {time.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    for image, occasion in EVAL_SET:
        t0 = time.time()
        r = analyze(image, occasion)
        dt = time.time() - t0
        j = r.get("judgment", {})
        p = r.get("perception", {})
        lines += [
            f"## {Path(image).name} — {occasion} ({dt:.0f}s)",
            "",
            f"**Perception:** {json.dumps(p.get('items', []), ensure_ascii=False)}"
            f" · modest: {p.get('modest_dress')}",
            f"**Scores:** {json.dumps(j.get('scores', {}))} · overall {j.get('overall')}",
            "",
            f"> {j.get('feedback', '(no feedback)')}",
            "",
            f"**One fix:** {j.get('one_fix', '(none)')}",
            "",
        ]
        print(f"{Path(image).name} [{occasion}] done in {dt:.0f}s")

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
