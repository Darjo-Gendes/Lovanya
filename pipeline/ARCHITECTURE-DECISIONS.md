# Lovanya AI Pipeline — Architecture Decisions (recreated)

> The original copy of this file (under `lovanya/design/claude-ui/uploads/files/`)
> was lost when the project was moved between machines and could not be
> recovered locally. This is a recreation from the project briefing, kept
> only as far as needed to rebuild the backend seams. If the original
> resurfaces, treat it as authoritative over this file.

## Locked decisions

1. **All open-weight, self-hosted models.** No Anthropic/OpenAI API calls at
   runtime. Everything must run locally against the GPU on this machine.
2. **Detection + segmentation:** GroundingDINO + SAM2 (not yet implemented —
   `pipeline/app/segment.py` is still a stub that returns the whole image).
3. **Perception + judgment:** Qwen2.5-VL-3B-Instruct (default). A 7B variant
   is documented as a fallback if 3B quality is insufficient, but 3B is what
   we target given the 8GB VRAM budget.
4. **Optional render step:** SDXL/Flux for a styled visual — out of scope for
   this pass.
5. **Structured, one-shot inference only.** Conversational/chat-style
   multi-turn AI was explicitly rejected to keep per-action cost and latency
   bounded. Do not add chat, agent loops, or multi-agent orchestration — this
   is a deliberate scope boundary, not a gap to fill in later.

## Three build seams that must stay real

- **Framework-as-file** — the styling rubric/voice lives in
  `pipeline/framework/styling-framework.md`, a plain text file, never
  hardcoded into Python. Judgment prompts must load this file at call time.
- **Output logging** — every judgment produced by an analyzer is appended to
  `pipeline/logs/judgments.jsonl` via `log_judgment()`, regardless of which
  model produced it.
- **Swappable model boundary** — `config.MODEL` (env var) selects the active
  analyzer in `pipeline/app/analyze.py`'s `get_analyzer()`. Swapping models
  must remain a one-line change (add a branch, nothing else).

## Current implementation status (this pass)

- `QwenAnalyzer` (`app/qwen_analyzer.py`) — perception + judgment via
  Qwen2.5-VL-3B-Instruct, one structured call per stage, no chat loop.
  Loads the framework file at judge time (framework-as-file seam).
- `segment.py` — real seam, stub implementation (returns the whole image).
  `analyze()` already calls it, so GroundingDINO+SAM2 slot in later without
  touching the pipeline shape. Deferred deliberately to keep scope tight.
- `app/main.py` — FastAPI server: `GET /` browser test bench (sample gallery
  + occasion picker + judgment view), `POST /api/analyze` (sample name or
  photo upload), `GET /api/samples`, `GET /health`, `POST /warmup`.
- `run_sample.py` — CLI single-photo harness.
- `samples/` — 30 real outfit photos (cropped from the user-provided grid).
- `HonestMockAnalyzer` — existed pre-move (GPU-free, color-math grounded);
  lost with the original zip and NOT recreated, since this machine runs the
  real model. The `MODEL` env var seam is where it would return if needed.

## Hardware this pipeline targets

- GPU: NVIDIA GeForce RTX 4060 Ti, 8188 MiB VRAM (confirmed via `nvidia-smi`
  on 2026-07-01). Real-world free VRAM varies with what else is running
  (browser, etc.) — budget accordingly when choosing precision/quantization.
