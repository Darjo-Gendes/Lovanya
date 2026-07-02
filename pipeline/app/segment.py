"""Stage 1 — detection + segmentation.

STUB. Real implementation (architecture-decisions.md): GroundingDINO does
open-vocabulary detection of the garment, SAM2 cuts it out, and we hand a clean,
isolated crop to the perception model. Until those weights are wired, this
returns the whole image as the "garment region" so the rest of the pipeline runs
end-to-end with no GPU.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class GarmentRegion:
    detected: bool
    crop: Optional[bytes]  # isolated garment image bytes (whole image in the stub)
    box: Optional[tuple]  # normalized (x0, y0, x1, y1)
    note: str


def segment(image: Optional[bytes]) -> GarmentRegion:
    if not image:
        return GarmentRegion(detected=False, crop=None, box=None, note="no image provided")
    # TODO(real): GroundingDINO('garment') -> SAM2 mask -> tight crop.
    return GarmentRegion(
        detected=True,
        crop=image,
        box=(0.0, 0.0, 1.0, 1.0),
        note="stub: whole image used as garment region",
    )
