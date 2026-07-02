# CLAUDE.md — Lovänya Wardrobe Auto-Fill Pipeline

Read this first. It orients you to the project and the non-negotiable decisions.

## What this is
The backend pipeline for Lovänya (mobile fashion identity app). A user uploads a
photo; the pipeline auto-fills their wardrobe with the garment, analyzed and
described. Linear flow:

```
photo → GroundingDINO + SAM2 (detect + segment garment)
      → Qwen2.5-VL (perception: describe → JSON  |  judgment: styling verdict)
      → SDXL/Flux (optional: clean product shot)
      → wardrobe entry (image + attributes + verdict JSON)
```

## Non-negotiable decisions (see docs/architecture-decisions.md for full rationale)
1. **All open-weight, self-hosted models.** No Anthropic/OpenAI API at runtime.
2. **Default VLM = Qwen2.5-VL-3B.** 7B is a documented fallback.
3. **Sophistication lives in `framework/styling-framework.md`, NOT in code.**
   The model renders that framework; it never freestyles styling advice.
4. **Structured one-shot inference. NOT conversational.** Do not add chat.
5. **Three build seams must always hold:** framework-as-file, output logging,
   swappable model boundary (same JSON in/out regardless of model).
6. **Runtime = serverless GPU (RunPod-class), scale-to-zero.** No owned hardware
   required; a local GPU is dev-only.

## Project layout
```
docs/
  architecture-decisions.md   # LOCKED decisions + rationale
  tier-and-compute-spec.md    # tiers, economics, phased rollout
framework/
  styling-framework.md        # the judgment rubric + brand voice (the moat)
app/                          # (to build) pipeline code
  segment.py                  #   GroundingDINO + SAM2
  analyze.py                  #   Qwen2.5-VL — perception + judgment
  render.py                   #   SDXL/Flux cleanup (optional)
  pipeline.py                 #   linear orchestrator
handler.py                    # (to build) RunPod serverless entrypoint
```

## Suggested first tasks when building
- Scaffold `app/` with the linear `pipeline.py` orchestrator and stubbed stages.
- Implement `analyze.py` to load `framework/styling-framework.md` at runtime and
  enforce the JSON output contract defined there.
- Wire output logging (input + output) from the start.
- Keep the model identifier in one config constant so the swap boundary is real.

## Style note for the operator
Sharp, no-fluff, concrete deliverables with strong editorial polish. Match that.
