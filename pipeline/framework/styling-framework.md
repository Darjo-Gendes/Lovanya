# Lovänya Styling Framework

This file is the **judgment layer's brain**. The model does not freestyle styling
advice — it scores and describes garments/outfits strictly against this rubric, in
this voice. Edit this file to tune sophistication and tone. Do NOT move this logic
into code.

> STATUS: STARTER — populate from the council document and brand guidelines.
> The structure is here; the substance is yours to fill and refine via pressure-testing.

---

## Voice contract
- Editorial, warm, precise. Never generic, never hype.
- Speaks to a Fashion Identity, not a score-chasing game.
- No leaderboard / competition framing. No appearance judgment of the person —
  only the styling of owned clothing.
- [TODO: paste Lovänya brand voice rules from brand guidelines]

---

## Evaluation dimensions
Each Outfit Check verdict is expressed against these. For each, define: what it
means, what raises it, what lowers it, and example phrasing.

### Color Harmony
- Meaning: how the colours relate (analogous / complementary / grounded by neutrals).
- Raises: tight analogous or clean complementary pairings; neutrals that anchor.
- Lowers: mid-distance saturated clashes.
### Elegance
- Meaning: restraint, polish, considered silhouette.
### Outfit Cohesion
- Meaning: everything reads as one intentional look.
### Confidence Boost
- Meaning: does it suit the wearer's stated feeling and occasion.
### Consistency
- Meaning: alignment with the wearer's established style identity.
### Style Growth
- Meaning: a gentle stretch beyond the usual, without losing the self.

---

## Garment attribute vocabulary (perception layer output)
Constrain the value sets so output is consistent, not free-text drift.

- `category`: [top, bottom, dress, outerwear, shoes, bag, accessory]
- `subcategory`: [TODO controlled list]
- `color_primary`: named palette (see app/color.py colour names), not raw hex
- `color_secondary`: named palette
- `pattern`: [solid, stripe, check, floral, print, textured]
- `formality`: [casual, smart-casual, business, formal]
- `fit`: [loose, regular, fitted]
- `season`: [all, spring, summer, autumn, winter]
- `notes`: short free-text, ≤ 1 sentence

---

## Output JSON contract (the swappable boundary)
The judgment layer always returns this shape, regardless of which model produces
it. This is what makes model swaps a one-line change. (Mirrored as Pydantic in
`app/contracts.py`: `Garment` + `Verdict` + `Analysis`.)

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
When reviewing logged outputs (`logs/judgments.jsonl`), flag any verdict that:
- [ ] Could apply to any outfit (generic) → tighten the dimension definitions
- [ ] Breaks brand voice → tighten the voice contract above
- [ ] Invents attributes not visible in the photo → constrain the prompt
- [ ] Judges the person rather than the styling → hard violation, fix prompt
