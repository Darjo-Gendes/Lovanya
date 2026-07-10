# Lovänya — Roadmap to Launch (locked 2026-07-08)

Bar: **launchable product**. Phasing decided with the operator; both machines
build from this file. Detailed specs: `pipeline/docs/visual-pipeline-v1.md`,
`lovanya/design/claude-ui/uploads/files/architecture-decisions.md`.

## Phase 1 — Finish the visible app *(UI PC · no money, no new services)*
- [x] Journal tab v1 (replaces History): Feed + Library shell, ribbon-only
      saves, look sheet reopens saved analyses, progressive disclosure.
      Cut by decision: style/mood labels (evidence-gated return in Phase 2),
      AI Collections (Phase 2), places search.
- [ ] Profile screen reconciled to canonical design
- [ ] Wardrobe final pixel pass vs `lovanya/public/prototype/lovanya-app.html`
- [ ] localStorage quota tripwire (warn, never silently drop; architecture
      stays deferred to Phase 3)
- [ ] Deploy to Vercel (PWA on the operator's phone; mock fallback keeps the
      app fully functional without the pipeline)

**Exit test:** daily use on a phone; nothing feels unfinished; no data loss.

## Phase 2 — Real AI serving *(GPU PC as home server · still $0)*
- [ ] Pipeline served from the GPU PC + tunnel; app flips via
      `NEXT_PUBLIC_PIPELINE_URL`
- [ ] Qwen3-VL-8B judge quality gate (QLoRA + 120-sample gold set, running)
- [ ] Per-garment segmentation → cutouts, embeddings (dedup internals),
      LookCard clarity/dominance metrics — emitting the `looks.json`
      interchange (`lovanya/lib/garment-json.ts`)
- [ ] AI garment thumbnails via local ComfyUI+Flux (plan committed on GPU PC)
- [ ] Journal Phase-2 features: extracted-items grids, garment↔look browsing,
      AI Collections; style labels return ONLY if judge label accuracy clears
      the gold-set bar

**Exit test:** a phone photo gets a real Qwen verdict and a catalog-grade
thumbnail.

## Phase 3 — Launch infrastructure *(money and accounts enter here, last)*
- [ ] Storage decision (deferred by design; schema now evidenced by the
      Journal/Look + Garment entities) — likely Supabase; migrate local-first
- [ ] Pipeline → RunPod serverless (`pipeline/handler.py`), spend alert
- [ ] Tier split per tier spec (free caps / premium), monitoring, abuse caps

**Exit test:** a stranger signs up, uses it, and the unit economics hold.

## Two-machine protocol (GitHub is the connector)

Two machines build one product; `main` on github.com/Darjo-Gendes/Lovanya is
the single source of truth. Every major adjustment is broadcast there.

- **GPU PC = the AI department.** Owns `pipeline/` — Qwen judge, GroundingDINO
  + SAM2, ComfyUI/Flux thumbnails, training. Serves the model.
- **This PC = the App.** Owns `lovanya/` — the Next.js app, screens, design.
- **Shared law, held to the same standard on both:**
  - Design: `.claude/skills/lovanya-design-director/` (committed — both PCs
    auto-load it for any UI work) + the identity core in `lovanya/AGENTS.md`.
  - AI: `pipeline/docs/*` + `architecture-decisions.md`.
  - Plan: this file.
- **Rhythm:** `git pull --rebase` before starting; push when a unit of work is
  green; `git fetch` before pushing (the other side moves fast). No force-push
  to `main`. Broadcast any locked decision as a commit, not just a memory.
- **Shareable canvas:** `lovanya/public/prototype/lovanya-app.artifact.html`
  (self-contained, fonts inlined) is committed and publishable as a Claude
  Artifact from either machine; rebuild it with
  `lovanya/scripts/build-artifact.py` after editing the canonical
  `lovanya-app.html`.

## Standing rules
- Two machines, one `main`: **always `git fetch` before pushing** — the other
  side moves fast.
- No conversational AI at runtime; structured one-shot inference only.
- The three seams stay real: framework-as-file, output logging, swappable
  model boundary.
