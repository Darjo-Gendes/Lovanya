"""Human/clothing semantic parser — the fix for SAM2's skin-bleed problem.

Root cause diagnosed 2026-07-14: box-prompted SAM2 is a GENERIC segmenter; it
has no concept of "garment" vs "skin", so on tiny (~245px) source photos it
routinely grabs wrist/shoulder/neck skin into a garment mask (the recurring
"skin and garment are roughly similar color" failure) or bleeds into an
adjacent layered garment. This module uses a model trained specifically to
tell them apart: SegFormer fine-tuned on the ATR parsing dataset
(mattmdjaga/segformer_b2_clothes) — its 18 classes include Face/Hair/Left-arm/
Right-arm/Left-leg/Right-leg as classes DISTINCT from garment classes, so skin
can be subtracted by construction rather than hoped away.

License note: NVIDIA's original SegFormer license is research/non-commercial.
Fine for this R&D phase; revisit before shipping (same posture as FLUX dev).

The parser doesn't cover jewelry/watch/belt/cap - SAM2 stays the fallback for
those, but even then this module's skin mask is subtracted from its result.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

_model = None
_processor = None

# mattmdjaga/segformer_b2_clothes label ids (ATR dataset)
BACKGROUND, HAT, HAIR, SUNGLASSES, UPPER, SKIRT, PANTS, DRESS, BELT = range(9)
LSHOE, RSHOE, FACE, LLEG, RLEG, LARM, RARM, BAG, SCARF = range(9, 18)

SKIN_CLASSES = {FACE, HAIR, LARM, RARM, LLEG, RLEG}

CATEGORY_CLASSES: dict[str, set[int]] = {
    "top": {UPPER}, "outerwear": {UPPER}, "dress": {DRESS, UPPER},
    "bottom": {PANTS, SKIRT}, "bag": {BAG}, "shoes": {LSHOE, RSHOE},
    "hijab": {HAT, SCARF, HAIR},
}


def _load():
    global _model, _processor
    if _model is None:
        import torch
        from transformers import AutoModelForSemanticSegmentation, SegformerImageProcessor
        _processor = SegformerImageProcessor.from_pretrained("mattmdjaga/segformer_b2_clothes")
        _model = AutoModelForSemanticSegmentation.from_pretrained("mattmdjaga/segformer_b2_clothes")
        _model.eval()
        if torch.cuda.is_available():
            _model.to("cuda")
    return _model, _processor


def parse(image: Image.Image) -> np.ndarray:
    """Full outfit photo -> HxW int array of ATR class ids (0-17)."""
    import torch
    model, processor = _load()
    dev = next(model.parameters()).device
    inputs = processor(images=image.convert("RGB"), return_tensors="pt").to(dev)
    with torch.no_grad():
        logits = model(**inputs).logits.cpu()
    up = torch.nn.functional.interpolate(
        logits, size=image.size[::-1], mode="bilinear", align_corners=False)
    return up.argmax(dim=1)[0].numpy()


def skin_mask(label_map: np.ndarray) -> np.ndarray:
    return np.isin(label_map, list(SKIN_CLASSES))


def garment_mask(label_map: np.ndarray, category: str) -> np.ndarray | None:
    """Boolean mask for this category's parser classes, or None if the parser
    has no class for it (jewelry/watch/belt/cap -> caller falls back to SAM2)."""
    classes = CATEGORY_CLASSES.get(category)
    if not classes:
        return None
    return np.isin(label_map, list(classes))
