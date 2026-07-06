"""Time the one-shot analyze path and confirm output quality on a few
samples. Run from the repo root: python pipeline/scripts/verify_oneshot.py"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline import config  # noqa: E402
from pipeline.app.analyze import analyze  # noqa: E402

SAMPLES = [
    ("samples/sample_r5c2.jpg", "work"),      # hijab (modesty)
    ("samples/sample_r1c1.jpg", "casual"),    # neutral
    ("samples/b4_r5c5.jpg", "interview"),     # outlier mismatch
]
PIPELINE_DIR = Path(__file__).resolve().parent.parent


def main():
    print(f"ONESHOT={config.ONESHOT}", flush=True)
    times = []
    for image, occasion in SAMPLES:
        t0 = time.time()
        r = analyze(str(PIPELINE_DIR / image), occasion)
        dt = time.time() - t0
        times.append(dt)
        j = r["judgment"]
        print(json.dumps({
            "image": Path(image).name, "occasion": occasion, "seconds": round(dt, 1),
            "has_scores": bool(j.get("scores")), "overall": j.get("overall"),
            "occasion_fit": j.get("scores", {}).get("occasion_fit"),
            "feedback": (j.get("feedback") or "")[:130],
            "one_fix": (j.get("one_fix") or "")[:90],
        }, ensure_ascii=False), flush=True)
    warm = times[1:] or times
    print(f"MEAN_WARM_SECONDS={sum(warm)/len(warm):.1f}", flush=True)


if __name__ == "__main__":
    main()
