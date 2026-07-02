# How to test the Lovänya AI pipeline

Everything runs locally on the RTX 4060 Ti — no API keys, no cloud.

## Option A — browser test bench (easiest)

From the `pipeline/` folder:

```
python -m uvicorn app.main:app --port 8000
```

Then open **http://localhost:8000** in a browser. You'll see all 30 sample
outfit photos in a gallery. Click one, pick an occasion, hit **Analyze**.

- The **first** analyze loads Qwen2.5-VL-3B into VRAM — measured ~50s.
  Every analyze after that takes ~35–40s (two model calls: perceive + judge).
- You can also upload any photo instead of using a sample.
- Tip: close Chrome/other GPU-heavy apps first; the model wants ~7GB VRAM.
  If it doesn't fit, layers spill to CPU automatically (works, just slower).

## Option B — command line, one photo at a time

```
python run_sample.py samples/sample_r1c1.jpg --occasion "date night"
```

Prints the full perception + judgment JSON.

## What to look at

- Every judgment is appended to `logs/judgments.jsonl` — this is the output
  log seam from the architecture plan.
- The judging rubric/voice lives in `framework/styling-framework.md`. Edit
  that file and re-run — the AI's judgment style changes with no code change
  (framework-as-file seam).
- The active model is chosen by the `MODEL` env var (default `qwen`) in
  `app/config.py` → `app/analyze.py:get_analyzer()` (swappable-model seam).

## Unit tests (no GPU needed)

```
python -m pytest tests -q
```
