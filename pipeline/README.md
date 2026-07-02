# Lovanya Pipeline (stub scaffold)

Open-weight, self-hosted wardrobe auto-fill / outfit-check pipeline. This pass is
the **runnable stub scaffold**: the structure and all three build seams are real;
the model stages are stubbed so it runs end-to-end with **no GPU**. Locked
decisions live in `lovanya/design/claude-ui/uploads/files/architecture-decisions.md`;
the visual layer (LookCards, dedup, segmentation-first) is locked in
`docs/visual-pipeline-v1.md`.

## Run
From the repo root (the folder containing both `lovanya/` and `pipeline/`):

```sh
python -m pip install -r pipeline/requirements.txt
python -m uvicorn pipeline.service:app --port 8000 --reload
# → http://localhost:8000/health   {"status":"ok","model":"honest-mock"}
```

Tests (no server needed):

```sh
python -m pytest pipeline/tests -q
```

## Pipeline

```
photo | palette → segment(stub) → analyze(swappable) → render(stub) → result
```

| File | Stage | Now | Real (later) |
|------|-------|-----|--------------|
| `app/segment.py` | detect + cut out garment | whole image | GroundingDINO + SAM2 |
| `app/analyze.py` | perceive + judge | HonestMock (ported colour logic) | **Qwen2.5-VL-3B** |
| `app/render.py` | clean product shot | none | SDXL / Flux |
| `app/pipeline.py` | linear one-shot orchestrator | ✓ | ✓ |

## The three locked seams (real from day one)
1. **Framework-as-file** — `framework/styling-framework.md` is loaded at runtime by `analyze.py`; tuning the voice/rubric is a text edit, not a code change.
2. **Output logging** — every judgment appends `{input, output}` to `logs/judgments.jsonl` for pressure-testing.
3. **Swappable model boundary** — `config.MODEL` selects the analyzer; all analyzers return the same `Perception` / `Verdict`, so the swap is one line.

## Swap in the real model
```sh
LOVANYA_MODEL=qwen2.5-vl-3b ...
```
then implement `QwenAnalyzer.perceive/judge` in `app/analyze.py` (load the VLM,
feed it the framework + isolated crop, return the same contract). Nothing else changes.

## Frontend wiring
`lovanya/lib/ai/index.ts` uses the pipeline when `NEXT_PUBLIC_PIPELINE_URL` is set
(e.g. `http://localhost:8000`), otherwise the local mock. The adapter
(`lib/ai/pipeline.ts`) **falls back to the mock on any error**, so the app never
breaks when the service is down.

```sh
# lovanya/.env.local
NEXT_PUBLIC_PIPELINE_URL=http://localhost:8000
```

## Deliberately NOT in this pass
Real weights, Docker/RunPod deploy, DB + object storage, batching/queue — added
only when the plan calls for them, never speculatively.
