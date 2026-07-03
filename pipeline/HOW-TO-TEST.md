# How to test the Lovänya AI pipeline

Everything runs locally on the RTX 4060 Ti — no API keys, no cloud.

## Option A — browser test bench (easiest)

From the **repo root** (not pipeline/ — the app imports as a package):

```
python -m uvicorn pipeline.app.main:app --port 8000
```

Then open **http://localhost:8000** in a browser. You'll see all 30 sample
outfit photos in a gallery. Click one, pick an occasion, hit **Analyze**.

- The judge is **Qwen3-VL-8B-Instruct** quantized to 4-bit at load
  (bitsandbytes NF4). The first analyze loads it into VRAM (expect a couple
  of minutes); after that each analyze runs two model calls (perceive +
  judge) plus a GroundingDINO garment-crop.
- Rate every judgment with 👍/👎 — a 👎 opens a correction box. Ratings and
  corrections go to `data/ratings.jsonl` and become fine-tuning data
  (see TRAINING.md).
- You can also upload any photo instead of using a sample.
- Tip: close Chrome/other GPU-heavy apps first; the model wants ~7GB VRAM.
  If it doesn't fit, layers spill to CPU automatically (works, just slower).

## Option B — command line, one photo at a time

From the repo root:

```
python pipeline/run_sample.py pipeline/samples/sample_r1c1.jpg --occasion "date night"
```

Add `LOVANYA_ADAPTER=pipeline/adapters/<timestamp>` before the command to
judge with a trained LoRA instead of the base model.

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

From the repo root:

```
python -m pytest pipeline/tests -q
```
