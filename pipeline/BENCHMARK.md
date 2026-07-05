# Judgment benchmark vs gold labels

- matched: **10** of 120 gold images (predictions from logs/judgments.jsonl)
- **overall score MAE: 0.9** (points off your gold label, lower is better)
- per-dimension MAE: color_harmony 1.1, occasion_fit 0.9, silhouette_balance 0.4, cohesion 1.1
- outlier recall: **2/3** deliberate mismatches flagged low (67%)
- mean latency: n/as

Interpretation: overall MAE under ~1.0 means the model tracks your taste closely; outlier recall is the important one — it must catch outfit/occasion mismatches, not just praise everything.