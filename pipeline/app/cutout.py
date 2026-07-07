"""Box-prompted SAM2 garment cutout — precise masks, on-GPU, zero tokens.

The fix for the matting bottleneck (review/matte_gpu/FINDING.md): BiRefNet is a
salient-object model, so on a garment crop it keeps the person. SAM2, prompted
with the exact GroundingDINO box, masks the GARMENT itself — no leftover arm or
hand. This clean cutout is what the render stage (imagegen.py) then turns into
a product shot.

Uses transformers' Sam2Model + Sam2Processor (no external sam2 package needed).
"""
from __future__ import annotations

import io

from PIL import Image

from .. import config

_model = None
_processor = None


def _get_sam2():
    global _model, _processor
    if _model is None:
        import torch
        from transformers import Sam2Model, Sam2Processor

        dev = "cuda" if torch.cuda.is_available() else "cpu"
        _model = Sam2Model.from_pretrained(config.SAM2_MODEL_ID).to(dev).eval()
        _processor = Sam2Processor.from_pretrained(config.SAM2_MODEL_ID)
    return _model, _processor


def sam2_mask(pil: Image.Image, box):
    """Return a boolean HxW mask for the garment in `box` (x0,y0,x1,y1 px)."""
    import numpy as np
    import torch

    model, processor = _get_sam2()
    inputs = processor(
        images=pil,
        input_boxes=[[[float(box[0]), float(box[1]), float(box[2]), float(box[3])]]],
        return_tensors="pt",
    ).to(model.device)
    with torch.no_grad():
        out = model(**inputs)
    masks = processor.post_process_masks(
        out.pred_masks.cpu(), inputs["original_sizes"].cpu()
    )[0]  # -> tensor [num_boxes, num_masks, H, W]
    scores = out.iou_scores.cpu()[0][0]  # [num_masks]
    m = masks[0]  # first (only) box -> [num_masks, H, W]
    best = int(scores.argmax())
    arr = m[best].numpy() if hasattr(m[best], "numpy") else np.asarray(m[best])
    return arr.astype(bool)


def sam2_cutout(pil: Image.Image, box) -> Image.Image:
    """Garment image (RGB) + box -> transparent RGBA cutout of just the garment."""
    import numpy as np

    mask = sam2_mask(pil, box)
    rgba = pil.convert("RGBA")
    a = (mask.astype("uint8") * 255)
    alpha = Image.fromarray(a, mode="L").resize(rgba.size)
    rgba.putalpha(alpha)
    # tight-crop to the mask bbox so the cutout isn't mostly empty
    ys, xs = np.where(mask)
    if len(xs) and len(ys):
        sx, sy = rgba.width / mask.shape[1], rgba.height / mask.shape[0]
        x0, x1 = int(xs.min() * sx), int(xs.max() * sx)
        y0, y1 = int(ys.min() * sy), int(ys.max() * sy)
        rgba = rgba.crop((x0, y0, max(x0 + 1, x1), max(y0 + 1, y1)))
    return rgba


def sam2_cutout_bytes(image_bytes: bytes, box) -> bytes:
    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    sam2_cutout(pil, box).save(buf, format="PNG")
    return buf.getvalue()
