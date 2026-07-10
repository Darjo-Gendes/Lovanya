"""Stage 3 — optional clean product shot (steady-format dispatch).

Turns a garment cutout (+ its attributes) into a Uniqlo/GU-style product shot
on white, via the steady prompt format in app/product_shot.py. The MODE seam
(config.PRODUCT_MODE) picks the generation angle — one dispatch, swappable:

  "faithful"  img2img from the cutout, low strength — closest to the real piece
  "balanced"  img2img from the cutout, higher strength — flatter/cleaner
  "idealized" txt2img from attributes only — generic clean catalogue (no cutout)

Optional by design: any failure (no image, model missing, OOM) degrades to
None and the caller keeps the plain cutout. Set LOVANYA_RENDER=off to skip.
"""
from __future__ import annotations

from typing import Optional

from .. import config

_STRENGTH = {"faithful": 0.45, "balanced": 0.68}


def render(crop: Optional[bytes], garment: str = "a clothing garment",
           color: str = "", details: str = "") -> Optional[bytes]:
    """Dispatch to the configured product-shot angle. `garment`/`color`/`details`
    are the auto-derived attributes (category + dominant color + perception)."""
    if getattr(config, "RENDER", "on") == "off":
        return None
    mode = getattr(config, "PRODUCT_MODE", "faithful")
    try:
        from .product_shot import product_shot, product_shot_from_ref

        # no cutout, or idealized mode -> pure txt2img from attributes
        if not crop or mode == "idealized":
            return product_shot(garment, color, details)
        return product_shot_from_ref(
            crop, garment, color, details, strength=_STRENGTH.get(mode, 0.45)
        )
    except Exception:
        # never break the pipeline for the optional clean shot
        return None
