"""Stage 3 — optional clean product shot.

SDXL img2img turns an isolated garment cutout into a standardized, catalogue-
style product shot for the wardrobe entry (see app/imagegen.py). Optional by
design: the pipeline is fully functional without it, so any failure (no image,
model missing, OOM) degrades gracefully to None — the caller keeps the cutout.

Set LOVANYA_RENDER=off to skip entirely.
"""
from __future__ import annotations

from typing import Optional

from .. import config


def render(crop: Optional[bytes]) -> Optional[bytes]:
    if not crop or getattr(config, "RENDER", "on") == "off":
        return None
    try:
        from .imagegen import render_product_shot

        return render_product_shot(crop)
    except Exception:
        # never break the pipeline for the optional clean shot
        return None
