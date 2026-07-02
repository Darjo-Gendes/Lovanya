# Training plan (decided 2026-07-02)

Goal: judgments approaching frontier-model quality, while staying open-weight
and self-hosted at runtime.

## Sequence

1. **Judge upgrade (done first, no training)** — Qwen3-VL-8B-Instruct AWQ
   4-bit (`cyankiwi/Qwen3-VL-8B-Instruct-AWQ-4bit`), fits the 8GB GPU fully.
   Selected via `QWEN_MODEL_ID`; the analyzer is model-agnostic.
2. **Data collection (ongoing, both sources)**
   - `data/gold.jsonl` — distilled gold judgments written offline by a
     frontier model (Claude) against the styling framework. Seed set: all 30
     samples. Offline distillation does not violate the no-API-at-runtime
     rule — that rule bounds per-action runtime cost.
   - `data/ratings.jsonl` — 👍/👎 plus optional corrections captured in the
     test bench via `POST /api/rate`, keyed by `judgment_id` to
     `logs/judgments.jsonl`. The user's taste, accumulated for free while
     testing.
3. **QLoRA fine-tune (deferred until ~300+ examples)** — run locally on the
   4060 Ti. Honest constraint: 8GB VRAM caps local training at the 3B/4B
   tier; the plan is to fine-tune Qwen3-VL-4B on the collected data and
   compare it against the untuned 8B judge. If the tuned 4B doesn't win,
   revisit venue (a one-off cloud run trains the 8B).

## Non-goals

- Training GroundingDINO/SAM2: unnecessary — zero-shot detection with
  garment-label prompts (see `app/segment.py`). Revisit only if detection
  demonstrably fails on real user photos.
- RLHF/preference optimization pipelines, reward models, eval harnesses at
  this stage: premature until the supervised set exists.

## Format note

Training pairs are (image, occasion, framework) → judgment JSON, i.e. the
same one-shot contract the runtime uses — the fine-tune bakes the framework's
rules in; the framework file stays as the runtime steering wheel on top.
