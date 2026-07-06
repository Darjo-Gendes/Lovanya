"""After hardening the framework, confirm outliers now score LOW while good
outfits STAY high. Run from repo root: python pipeline/scripts/verify_recalibration.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline.app.analyze import analyze  # noqa: E402

PIPELINE = Path(__file__).resolve().parent.parent

# (image, occasion, expect) — outliers should drop to <=4; good should stay >=7
CASES = [
    ("samples/b4_r5c6.jpg", "wedding", "LOW"),
    ("samples/b2_r5c1.jpg", "belanja ke pasar", "LOW"),
    ("samples/b4_r5c5.jpg", "interview", "LOW"),
    ("samples/sample_r5c2.jpg", "work", "HIGH"),      # hijab — must stay high
    ("samples/sample_r1c1.jpg", "casual", "HIGH"),    # good neutral — must stay high
]


def main():
    for image, occasion, expect in CASES:
        r = analyze(str(PIPELINE / image), occasion)
        j = r["judgment"]
        ov = j.get("overall")
        ok = (ov <= 4) if expect == "LOW" else (ov >= 7)
        print(json.dumps({
            "image": Path(image).name, "occasion": occasion,
            "expect": expect, "overall": ov,
            "occasion_fit": j.get("scores", {}).get("occasion_fit"),
            "PASS": ok, "feedback": (j.get("feedback") or "")[:150],
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
