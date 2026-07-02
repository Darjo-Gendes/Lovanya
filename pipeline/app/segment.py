"""Detection + segmentation stage (GroundingDINO, zero-shot).

Detects the person and garments, crops the union box (with margin) so the
judge sees the outfit rather than mirrors/background clutter. No training
needed — labels below are open-vocabulary prompts.

SAM2 pixel masks are deliberately not wired yet: masked-out backgrounds hurt
VLM perception, so masks only become useful for the training-data phase
(garment cutouts). When that lands it must slot in behind this same
segment() signature.

Set SEGMENT=off to bypass (returns the whole image, the old stub behavior).
"""

import os
import tempfile

from PIL import Image

from . import config

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


def segment(image_path: str) -> str:
    """Return the path of the image region to analyze.

    GroundingDINO finds person/garment boxes; the union box (plus margin)
    is cropped and saved to a temp file. Falls back to the original image
    when detection is off, finds nothing, or errors.
    """
    if config.SEGMENT != "dino":
        return image_path

    try:
        detector = _get_detector()
        image = Image.open(image_path).convert("RGB")
        results = detector(image, candidate_labels=GARMENT_LABELS)
        boxes = [r["box"] for r in results if r["score"] >= MIN_SCORE]
        if not boxes:
            return image_path

        x0 = min(b["xmin"] for b in boxes)
        y0 = min(b["ymin"] for b in boxes)
        x1 = max(b["xmax"] for b in boxes)
        y1 = max(b["ymax"] for b in boxes)

        mx = (x1 - x0) * MARGIN
        my = (y1 - y0) * MARGIN
        x0 = max(0, int(x0 - mx))
        y0 = max(0, int(y0 - my))
        x1 = min(image.width, int(x1 + mx))
        y1 = min(image.height, int(y1 + my))

        # A crop that barely trims anything isn't worth the resave
        if (x1 - x0) * (y1 - y0) > 0.92 * image.width * image.height:
            return image_path

        fd, out_path = tempfile.mkstemp(suffix=".jpg", prefix="lv_crop_")
        os.close(fd)
        image.crop((x0, y0, x1, y1)).save(out_path, quality=92)
        return out_path
    except Exception:
        # Detection must never break the pipeline; judge the full photo.
        return image_path
