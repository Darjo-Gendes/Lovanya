# GPU per-garment matting — BiRefNet on tight crops (4060 Ti, 2026-07-06)

Resolves the open question from `../README.md` (findings #3/#4): the UI-PC
could not run per-garment BiRefNet on CPU, so the fair test was missing. Run
here on the GPU via `scripts/matte_garments.py` (GroundingDINO detect → tight
crop → BiRefNet matte per garment). Detection reuses `extract_garments.py`
and reproduced the UI-PC counts exactly (sample_r1c5 → 5, b4_r4c4 → 3).

## Result: BiRefNet on tight crops is NOT sufficient for garment cutouts.

Opaque-pixel % kept per cutout (checkerboard preview in `index.html`):

| garment | % kept | what actually happened |
|---|---|---|
| accessory·watch | 96.8% | whole tiny crop kept — no cutout at all |
| bag·tote (r1c5) | 96.7% | whole crop kept |
| shoes·sneakers | 96.7% | whole crop kept |
| bottom·pants | 78–83% | pants + background wall retained |
| top·t-shirt | 60–65% | keeps the **person** (face, arms), not just the top |
| outerwear·blazer | 60–64% | keeps the person + background |

**Why:** BiRefNet is a *salient-object* matting model. On a tight
garment-on-body crop the salient object is the person, so it keeps the person;
on a small accessory crop the whole rectangle is "foreground", so it keeps
everything. Neither isolates the garment.

## Conclusion (confirms UI-PC finding #4)
Whole-photo vs crop salient matting is the wrong axis. The garment must be
masked by its **exact detection box**, not salient-detected. The validated
next step is **box-prompted SAM2** on this GPU: feed SAM2 the GroundingDINO
box as a prompt so the mask is the garment, not the wearer. BiRefNet can then
be dropped from the cutout path (or kept only as a fallback refiner).

Speed was never the issue: ~2–4 s/garment on the 4060 Ti (vs slow CPU).
