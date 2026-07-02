# Lovänya Pipeline — Architecture Decisions (LOCKED)

This document records the decisions that define the wardrobe auto-fill pipeline.
Treat these as settled unless explicitly revisited. Rationale included so the
"why" survives.

---

## Core position

**Self-sustaining, open-model, all-free pipeline.** No closed-AI provider calls at
runtime. Cost scales with *actions*, not engagement. One-person operable.

---

## Locked decisions

### 1. Models — all open-weight, self-hosted
| Layer | Model | Job |
|---|---|---|
| Detection | GroundingDINO | Find garments (open-vocabulary boxes) |
| Segmentation | SAM2 | Cut the garment out of the photo |
| Perception + Judgment | **Qwen2.5-VL** | Describe garment → JSON; render styling verdict |
| Render (optional) | SDXL / Flux (img2img) | Clean standardized product shot |

- **Default VLM: Qwen2.5-VL-3B** (~4–5GB VRAM, cheap, fast). Sufficient because
  segmentation hands it a clean isolated garment — it only does the easy
  "describe this thing" job.
- **Qwen2.5-VL-7B** kept as a documented option for heavier judgment if needed.
- No Anthropic/OpenAI API at runtime. (Claude Code is the *build tool*, paid via
  subscription — fully decoupled from user volume.)

### 2. Sophistication comes from the framework, NOT the model
The judgment layer does **not** freestyle styling advice (that's where models go
generic). It executes a defined rubric + brand voice:
- Dimensions: Color Harmony, Elegance, Outfit Cohesion, Confidence Boost,
  Consistency, Style Growth (from the council document).
- Output is on-brand, editorial, consistent — because it's constrained.
- **The styling framework is the product moat, not the model weights.**

### 3. Structured one-shot inference — NOT conversational
Pipeline is linear and bounded: photo → JSON → verdict → done.
- **Rejected: conversational AI.** Reasons: (a) unbounded cost breaks the
  per-action economics; (b) good open-ended chat needs a far larger/heavier
  model; (c) it dilutes the product — Lovänya is a Fashion Identity platform, not
  a chatbot. Constraint *is* the sophistication.
- Conversation may return later ONLY as a bounded, premium, revenue-covered
  feature (e.g. capped follow-ups about a specific Outfit Check result). Not in
  scope now.

### 4. All-free posture for launch
Everything runs open/free. Premium ($3.50/mo) and free-tier caps are economic
levers (see tier spec), but the *technology* is identical across tiers at launch.
Pressure-test output quality once running; if judgment feels generic, the escape
hatch is Path B below — a known, ready option, not a redesign.

### 5. Build seams (must exist from day one — painful to retrofit)
- **Framework-as-file**: styling rubric + brand voice live in a single editable
  file (`framework/styling-framework.md`), NOT buried in code. Tuning voice =
  text edit, not code change.
- **Output logging**: every judgment logs input (garment/outfit) + output, so
  pressure-testing reviews real cases instead of re-generating.
- **Swappable model boundary**: the judgment call takes the same JSON contract in
  and out regardless of model, so swapping Qwen → a stronger model later is a
  one-line change.

---

## Carried forward from prior Lovänya architecture (unchanged)
- Three-layer model: **Analysis / Rendering / Mesh**.
- Rendering = Three.js/WebGL, client-side, zero tokens, free. **100% reused.**
- No AI mesh generation. Single chibi base mesh + blend shapes + bone scaling;
  garment deform via scaling (loose) / weight-transfer skinning (fitted).
- Avatar tab = private dress-up space. **Postponed to a future release.**
- Scaling patterns reused: async queue, batching, CDN for templates/textures.
- Only change vs. prior plan: the analysis model swapped Claude/GPT-vision →
  Qwen (same JSON contract, self-hosted, free).

---

## Escape hatches (documented, not active)
- **Path B (premium judgment):** reserve a closed-model API call for premium-tier
  deep styling reads only, covered by subscription revenue. Swappable boundary
  (decision 5) makes this a config change.
- **Fine-tune:** small Qwen fine-tune on own wardrobe data if generic accuracy
  falls short on local fashion specifics. Cheap to run, needs a dataset.

---

## Infrastructure (one-person operable)
- **Production runtime:** serverless GPU (RunPod-class), scale-to-zero,
  pay-per-second. ~$5–50/mo at early scale.
- **No owned hardware required.** Optional: a used RTX 3090 (24GB) as a local
  dev box to eliminate cloud cost *while building* — but production stays
  serverless for reliability (a home box is a single point of failure).
- **Provide:** RunPod account, a cheap CPU backend + DB (Supabase/Railway),
  object storage (R2/S3). Model weights are free from Hugging Face.
- **Phased cost control:** launch as deliberate loss leader (flex, full path),
  flip to cheap-path + batching only when user density makes batching painless.
  Spend alert set below provider ceiling as solo-operator safeguard.
