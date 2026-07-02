"""Standalone Qwen analyzer test harness.

Run a single sample photo through perceive() + judge() and print the result.
First run downloads and loads the Qwen2.5-VL-3B-Instruct weights, which takes
a while - subsequent runs in the same process would be fast, but each CLI
invocation reloads the model since this is meant for one-off manual testing.

Usage (from the repo root):
    python pipeline/run_sample.py pipeline/samples/my_outfit.jpg --occasion "date night"
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.app.analyze import analyze  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Path to a sample outfit photo")
    parser.add_argument(
        "--occasion",
        default="casual",
        help="Occasion context, e.g. 'work', 'date night', 'formal event'",
    )
    args = parser.parse_args()

    if not Path(args.image).exists():
        sys.exit(f"Image not found: {args.image}")

    t0 = time.time()
    result = analyze(args.image, args.occasion)
    elapsed = time.time() - t0

    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n(done in {elapsed:.1f}s, logged to pipeline/logs/judgments.jsonl)", file=sys.stderr)


if __name__ == "__main__":
    main()
