# Lovänya Styling Framework

This file is the **judgment layer's brain**. The VLM does not freestyle styling
advice — it scores and describes garments/outfits strictly against this rubric, in
this voice. Edit this file to tune sophistication and tone. Do NOT move this logic
into code.

> STATUS: STARTER — populate from the council document and brand guidelines.
> The structure is here; the substance is yours to fill and refine via pressure-testing.

---

## Voice contract
- Editorial, warm, precise. Never generic, never hype.
- Speaks to a Fashion Identity, not a score-chasing game.
- No leaderboard/competition framing. No appearance judgment of the person —
  only the styling of owned clothing.
- [TODO: paste Lovänya brand voice rules from brand guidelines]

---

## Evaluation dimensions
Each Outfit Check verdict is expressed against these (from the council document).
Define, for each: what it means, what raises it, what lowers it, and example phrasing.

### Color Harmony
- Meaning: [TODO]
- Raises: [TODO]
- Lowers: [TODO]
- Example phrasing: [TODO]

### Elegance
- Meaning: [TODO]
### Outfit Cohesion
- Meaning: [TODO]
### Confidence Boost
- Meaning: [TODO]
### Consistency
- Meaning: [TODO]
### Style Growth
- Meaning: [TODO]

---

## Garment attribute vocabulary (perception layer output)
The VLM extraction returns these fields. Constrain the value sets so output is
consistent, not free-text drift.

- `category`: [top, bottom, dress, outerwear, footwear, accessory, ...]
- `subcategory`: [TODO controlled list]
- `color_primary`: [TODO — named palette, not raw hex guesses]
- `color_secondary`: [TODO]
- `pattern`: [solid, stripe, check, floral, print, textured, ...]
- `formality`: [casual, smart-casual, business, formal, ...]
- `fit`: [loose, regular, fitted, ...]
- `season`: [TODO]
- `notes`: short free-text, ≤ 1 sentence

---

## Output JSON contract (the swappable boundary)
Judgment layer always returns this shape, regardless of which model produces it.
This is what makes Qwen → stronger-model swaps a one-line change.

```json
{
  "garment": { "...": "attribute fields above" },
  "verdict": {
    "dimension_scores": {
      "color_harmony": 0,
      "elegance": 0,
      "outfit_cohesion": 0,
      "confidence_boost": 0,
      "consistency": 0,
      "style_growth": 0
    },
    "editorial_read": "string — the on-brand styling verdict",
    "elevate_suggestions": ["string", "string"]
  }
}
```

---

## Pressure-test checklist
When reviewing logged outputs, flag any verdict that:
- [ ] Could apply to any outfit (generic) → tighten the dimension definitions
- [ ] Breaks brand voice → tighten the voice contract above
- [ ] Invents attributes not visible in the photo → constrain the prompt
- [ ] Judges the person rather than the styling → hard violation, fix prompt
