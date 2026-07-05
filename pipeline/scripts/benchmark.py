"""Objective quality benchmark: score the model's judgments against the gold
labels — a hard number so "is it good?" has an answer without a human rater.

Sources of predictions (in priority order per image):
  1. a --results JSONL of {image, occasion, judgment} records, if given;
  2. otherwise pipeline/logs/judgments.jsonl (the most recent judgment logged
     per image — i.e. whatever model last ran it).

Metrics vs data/gold.jsonl (matched by image basename):
  - overall MAE and per-dimension MAE (lower = closer to your taste);
  - outlier recall: of the gold "mismatch" outfits (gold overall <= 4), how
    many did the model also flag low (overall <= 6 OR occasion_fit <= 5);
  - mean latency if the records carry elapsed_seconds.

Run from the repo root:
    python pipeline/scripts/benchmark.py [--results some.jsonl] [--out BENCHMARK.md]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

PIPELINE_DIR = Path(__file__).resolve().parent.parent
DIMS = ["color_harmony", "occasion_fit", "silhouette_balance", "cohesion"]


def load_gold():
    gold = {}
    for line in (PIPELINE_DIR / "data" / "gold.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        gold[Path(r["image"]).name] = r
    return gold


def load_predictions(results_path):
    """image basename -> {scores, overall, elapsed} using the LAST record per image."""
    preds = {}
    if results_path and Path(results_path).exists():
        for line in Path(results_path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            j = r.get("judgment", {})
            preds[Path(r["image"]).name] = {
                "scores": j.get("scores", {}), "overall": j.get("overall"),
                "elapsed": r.get("elapsed_seconds"),
            }
        return preds
    log = PIPELINE_DIR / "logs" / "judgments.jsonl"
    if not log.exists():
        return preds
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        img = r.get("input", {}).get("image_path")
        j = r.get("output", {}).get("judgment", {})
        if img and isinstance(j, dict) and "overall" in j:
            preds[Path(img).name] = {  # later lines overwrite -> most recent wins
                "scores": j.get("scores", {}), "overall": j.get("overall"),
                "elapsed": None,
            }
    return preds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=None)
    parser.add_argument("--out", default=str(PIPELINE_DIR / "BENCHMARK.md"))
    args = parser.parse_args()

    gold = load_gold()
    preds = load_predictions(args.results)
    matched = [k for k in gold if k in preds and preds[k]["overall"] is not None]

    overall_err, dim_err = [], {d: [] for d in DIMS}
    latencies = []
    outlier_total, outlier_caught = 0, 0
    for k in matched:
        g, p = gold[k], preds[k]
        overall_err.append(abs(g["overall"] - p["overall"]))
        for d in DIMS:
            if d in g["scores"] and d in p["scores"]:
                dim_err[d].append(abs(g["scores"][d] - p["scores"][d]))
        if p["elapsed"]:
            latencies.append(p["elapsed"])
        if g["overall"] <= 4:  # a deliberate mismatch outlier
            outlier_total += 1
            if p["overall"] <= 6 or p["scores"].get("occasion_fit", 10) <= 5:
                outlier_caught += 1

    def mae(xs):
        return round(statistics.mean(xs), 2) if xs else None

    lines = [
        "# Judgment benchmark vs gold labels",
        "",
        f"- matched: **{len(matched)}** of {len(gold)} gold images "
        f"(predictions from {'--results' if args.results else 'logs/judgments.jsonl'})",
        f"- **overall score MAE: {mae(overall_err)}** (points off your gold label, lower is better)",
        "- per-dimension MAE: " + ", ".join(f"{d} {mae(dim_err[d])}" for d in DIMS),
        f"- outlier recall: **{outlier_caught}/{outlier_total}** deliberate mismatches flagged low"
        + (f" ({round(100*outlier_caught/outlier_total)}%)" if outlier_total else ""),
        f"- mean latency: {round(statistics.mean(latencies),1) if latencies else 'n/a'}s",
        "",
        "Interpretation: overall MAE under ~1.0 means the model tracks your "
        "taste closely; outlier recall is the important one — it must catch "
        "outfit/occasion mismatches, not just praise everything.",
    ]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
