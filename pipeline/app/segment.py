"""Stage 1 — detection + segmentation (GroundingDINO, zero-shot).

Real implementation of the visual-pipeline-v1.md gate: GroundingDINO detects
person/garments (open-vocabulary labels, no training), the union box (with
margin) is cropped, and a deterministic quality score (normalized
Laplacian-variance sharpness, per the spec) accompanies the region.

SAM2 pixel-mask cutouts are the next increment behind this same interface:
the box crop already feeds the judge (masked backgrounds hurt VLM judging),
while LookCards will consume the SAM2 cutout when it lands.

Set LOVANYA_SEGMENT=off to bypass (whole image, the old stub behavior).

Two entry points for the two call paths:
- `segment(bytes)`      -> GarmentRegion   (app service path: photo arrives as bytes)
- `segment_path(path)`  -> path            (bench/CLI path: photo lives on disk)
"""
from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from .. import config

GARMENT_LABELS = [
    "person", "shirt", "t-shirt", "blouse", "dress", "skirt", "pants",
    "jeans", "shorts", "jacket", "coat", "hijab", "bag", "shoes",
]

MARGIN = 0.06  # fraction of crop size added around the union box
MIN_SCORE = 0.35

_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        import torch
        from transformers import pipeline

        _detector = pipeline(
            "zero-shot-object-detection",
            model="IDEA-Research/grounding-dino-tiny",
            device=0 if torch.cuda.is_available() else -1,
        )
    return _detector


@dataclass
class GarmentRegion:
    detected: bool
    crop: Optional[bytes]  # isolated garment image bytes
    box: Optional[tuple]  # normalized (x0, y0, x1, y1)
    note: str
    quality_score: float = 0.0  # normalized Laplacian-variance sharpness


def quality_score(image: Image.Image) -> float:
    """Sharpness/usability of a region: normalized Laplacian variance
    (visual-pipeline-v1.md). 0 = unusably soft, ~1 = crisp."""
    import numpy as np

    gray = np.asarray(image.convert("L"), dtype=np.float64)
    lap = (
        -4 * gray
        + np.roll(gray, 1, 0) + np.roll(gray, -1, 0)
        + np.roll(gray, 1, 1) + np.roll(gray, -1, 1)
    )
    # 500 ≈ variance of a sharp photo at these resolutions; clamp to [0, 1]
    return min(1.0, lap.var() / 500.0)


def _detect_union_box(image: Image.Image) -> Optional[tuple]:
    """Run GroundingDINO, return the pixel-space union box or None."""
    detector = _get_detector()
    results = detector(image, candidate_labels=GARMENT_LABELS)
    boxes = [r["box"] for r in results if r["score"] >= MIN_SCORE]
    if not boxes:
        return None
    x0 = min(b["xmin"] for b in boxes)
    y0 = min(b["ymin"] for b in boxes)
    x1 = max(b["xmax"] for b in boxes)
    y1 = max(b["ymax"] for b in boxes)
    mx = (x1 - x0) * MARGIN
    my = (y1 - y0) * MARGIN
    return (
        max(0, int(x0 - mx)),
        max(0, int(y0 - my)),
        min(image.width, int(x1 + mx)),
        min(image.height, int(y1 + my)),
    )


def segment(image: Optional[bytes]) -> GarmentRegion:
    if not image:
        return GarmentRegion(detected=False, crop=None, box=None, note="no image provided")
    try:
        pil = Image.open(io.BytesIO(image)).convert("RGB")
    except Exception:
        return GarmentRegion(detected=False, crop=None, box=None, note="unreadable image")

    if config.SEGMENT != "dino":
        return GarmentRegion(
            detected=True, crop=image, box=(0.0, 0.0, 1.0, 1.0),
            note="segmentation off: whole image used",
            quality_score=quality_score(pil),
        )
    try:
        box = _detect_union_box(pil)
        if box is None:
            return GarmentRegion(
                detected=False, crop=image, box=(0.0, 0.0, 1.0, 1.0),
                note="no garment detected; whole image used",
                quality_score=quality_score(pil),
            )
        cropped = pil.crop(box)
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=92)
        norm = (
            box[0] / pil.width, box[1] / pil.height,
            box[2] / pil.width, box[3] / pil.height,
        )
        return GarmentRegion(
            detected=True, crop=buf.getvalue(), box=norm,
            note="grounding-dino union box crop",
            quality_score=quality_score(cropped),
        )
    except Exception as e:
        return GarmentRegion(
            detected=False, crop=image, box=(0.0, 0.0, 1.0, 1.0),
            note=f"detection error ({type(e).__name__}); whole image used",
            quality_score=quality_score(pil),
        )


def segment_path(image_path: str) -> str:
    """Return the path of the image region to analyze.

    Same detection as segment(), file-path flavored. Falls back to the
    original image when detection is off, finds nothing, or errors.
    """
    if config.SEGMENT != "dino":
        return image_path
    try:
        image = Image.open(image_path).convert("RGB")
        box = _detect_union_box(image)
        if box is None:
            return image_path
        # A crop that barely trims anything isn't worth the resave
        if (box[2] - box[0]) * (box[3] - box[1]) > 0.92 * image.width * image.height:
            return image_path
        fd, out_path = tempfile.mkstemp(suffix=".jpg", prefix="lv_crop_")
        os.close(fd)
        image.crop(box).save(out_path, quality=92)
        return out_path
    except Exception:
        # Detection must never break the pipeline; judge the full photo.
        return image_path
