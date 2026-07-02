# Lovänya Visual Pipeline v1 — LookCards (LOCKED 2026-07-02)

Companion to `architecture-decisions.md` (models + infra). This document locks
the **visual intelligence layer**: garment photos → structured, deduplicated
wardrobe → deterministic LookCard visuals. Treat these as settled unless
explicitly revisited. Both machines (UI PC and GPU PC) build from this file.

---

## Goal

Transform user-uploaded garment/outfit photos into structured garment data, a
deduplicated wardrobe, session-grouped outfits, and deterministic on-brand
visual thumbnails (**LookCards**) consumed by the Wardrobe / History / Profile
screens — with **no AI image generation**.

---

## Pipeline (corrected order — segmentation is the foundation, not optional)

```
[1] upload
[2] segment          GroundingDINO + SAM2 → clean garment cutout + quality score
[3] perceive + embed Qwen2.5-VL → attributes JSON; open-weight image embedding
                     (CLIP/SigLIP-class) computed on the CUTOUT, never raw photo
[4] dedup            exact hash → embedding similarity → USER CONFIRMATION
[5] store            canonical garments + linked variants (storage-agnostic contracts)
[6] outfit grouping  session-based ONLY
[7] LookCard build   hero selection + deterministic layout rules
[8] render           DOM/Canvas → thumbnail (no generative models)
[9] UI consumption   Wardrobe / History / Profile
```

---

## Locked v1 decisions (chosen 2026-07-02)

1. **Segmentation first.** GroundingDINO+SAM2 is wired **before** LookCards
   ship. A LookCard collaged from raw photos (messy backgrounds, mixed
   lighting) reads as a scrapbook, not an editorial card — below this
   product's quality bar. The renderer consumes clean cutouts from day one.
2. **Dedup asks, never silently merges.** On suspected duplicate: "Looks like
   your White Linen Shirt — same piece?" A false merge silently corrupts the
   wardrobe and is worse than a duplicate. Auto-merge is rejected.
3. **Storage deferred.** Prove the segmentation → LookCard chain end-to-end
   first; then decide Supabase vs local-first. Until then all contracts are
   designed storage-agnostic (no schema assumes a specific backend).
4. **Machine split.** GPU PC (clone of this repo) does model work:
   `segment.py`, the embedding endpoint, `QwenAnalyzer` tagging. The UI PC
   does the LookCard contract, deterministic renderer, dedup-confirm UX, and
   app wiring. Gate: LookCards do not ship until cutouts are real.

---

## Amendments to the original draft spec (and why)

| Original draft | Locked v1 | Why |
|---|---|---|
| Background removal "optional later" | Mandatory stage 2 | The single biggest visual-quality lever; everything downstream consumes cutouts |
| Embed the uploaded photo | Embed the segmented cutout | Otherwise background dominates similarity and dedup breaks |
| `cosine > 0.92 → merge as variant` | Conservative threshold, calibrated on real data, **+ user confirmation** | 0.92 is a magic number; false merges are user-visible corruption |
| Outfit grouping by "embedding co-occurrence cluster" | Session-based grouping only | Visually similar ≠ worn together; clustering produces wrong outfits |
| `visual_clarity`, `style_dominance` undefined | `visual_clarity` = normalized Laplacian-variance sharpness of the cutout; `style_dominance` = normalized pixel area of the garment within its outfit photo × category weight | Deterministic scoring needs concrete formulas |
| Manual / optional AI tagging | Qwen2.5-VL perception (per architecture-decisions.md) | Accuracy for high-standard users lives here; manual doesn't scale, mock isn't accurate |

Dropped entirely: SDXL/Flux render stage (was already optional; this spec
replaces it with deterministic composition).

---

## Contracts (storage-agnostic)

Reconcile with `pipeline/app/contracts.py` — extend the existing `Garment`
model; do not create a parallel one.

```ts
Garment {
  id, user_id, image_url,            // raw upload
  cutout_url,                        // segmented garment (stage 2 output)
  category: "top"|"bottom"|"dress"|"outerwear"|"shoes"|"bag"|"accessory",
  attributes: { colors: string[], material?, style_tags: string[], season?: string[] },
  embedding: number[],               // of the cutout
  quality_score: number,             // sharpness/usability of the cutout
  canonical_id?: string,             // set when user confirms "same piece"
  created_at
}

Outfit {
  id, garment_ids: string[],
  occasion?, style_summary,
  created_at                         // grouping key: upload/analyze session
}

LookCard {
  id, outfit_id,
  title, subtitle, caption,
  layout_type: "center"|"diagonal"|"stack"|"grid",
  hero_garment_id,
  palette: string[],                 // from the existing colour engine
  thumbnail_url
}
```

**Layout rules (deterministic):** 1 garment → `center` · 2 → `diagonal` ·
3–4 → `stack` · 5+ → `grid`.

**Hero scoring:**
```
score = visual_clarity·0.35 + category_weight·0.25 + style_dominance·0.20
      + recency·0.10 + user_favorite_bias·0.10
category priority: outerwear > dress > top > bottom > shoes > accessory
```
Constant tables live in code, next to the scorer.

---

## Critical rules (do not break)

1. No AI image generation.
2. Deterministic layouts — same inputs, same card, every render.
3. Hero garment is stable per outfit.
4. Dedup before visualization.
5. Embeddings on the cutout, never the raw photo.
6. No silent merges — ever.
7. UI is a renderer, not a generator.
8. Design reference for LookCards: the share/snap card in
   `lovanya/public/prototype/lovanya-app.html`.

---

## Build order

1. **Gate (GPU PC):** real `segment.py` — cutout + quality score from a photo.
2. **Parallel (UI PC):** LookCard contract + deterministic renderer, developed
   against a handful of hand-cut fixture images; dedup-confirm UX.
3. **Integration:** embeddings + Qwen tagging feed dedup and LookCards.
4. **Then** the storage decision (Supabase vs local-first) — not before.
