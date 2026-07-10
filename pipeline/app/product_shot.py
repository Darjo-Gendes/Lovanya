"""Steady-format product-shot generation — Uniqlo/GU-style catalogue images.

One locked prompt template so every garment comes out in the SAME format:
flat ghost-mannequin, front view, pure white background, even lighting. Driven
by garment attributes (type + color + details) from detection/perception.

Two modes, both local/on-GPU/zero-tokens (SDXL):
  - txt2img  (default): clean idealized product shot from attributes. Most
    consistent, best matches the Uniqlo references (flat, no body).
  - img2img  (--ref): use a garment cutout as a loose reference for shape/color.

The steady format lives in STYLE / NEGATIVE / PARAMS below — edit there to
retune every future product shot at once (framework-as-file spirit).
"""
from __future__ import annotations

import io

from .. import config

# ---- THE STEADY FORMAT -------------------------------------------------------
# subject is the only variable part; everything else is locked for consistency.
STYLE = (
    "flat lay ghost-mannequin e-commerce product photograph, front view, "
    "single garment centered and fully in frame, pure white seamless background, "
    "soft even shadowless studio lighting, sharp focus, crisp fabric texture, "
    "true accurate color, clean minimal catalogue product shot, high resolution"
)
NEGATIVE = (
    "person, model, human, face, hands, arms, body, skin, mannequin head, neck, "
    "hanger, coat rack, folded pile, drop shadow, cast shadow, gradient, colored "
    "background, grey background, props, text, watermark, logo, brand name, "
    "multiple items, collage, blurry, lowres, deformed, cropped, out of frame"
)
PARAMS = dict(width=896, height=1152, num_inference_steps=30, guidance_scale=7.0)
# ------------------------------------------------------------------------------

_txt = None
_img = None


def build_prompt(garment: str, color: str = "", details: str = "") -> str:
    """subject + locked STYLE. e.g. garment='henley long-sleeve top',
    color='light grey', details='ribbed, quarter-button placket'."""
    subject = " ".join(p for p in [color, garment] if p).strip()
    if details:
        subject += f", {details}"
    return f"{subject}, {STYLE}"


def _txt_pipe():
    global _txt
    if _txt is None:
        import torch
        from diffusers import StableDiffusionXLPipeline

        cuda = torch.cuda.is_available()
        _txt = StableDiffusionXLPipeline.from_pretrained(
            config.IMAGE_MODEL_ID,
            torch_dtype=torch.float16 if cuda else torch.float32,
            variant="fp16" if cuda else None, use_safetensors=True,
        )
        if cuda:
            _txt.enable_model_cpu_offload(); _txt.enable_vae_slicing()
        else:
            _txt.to("cpu")
    return _txt


def _img_pipe():
    """img2img pipeline. Loads its own copy from_pretrained — from_pipe() on a
    cpu-offloaded txt2img pipe leaves broken offload hooks that hang the GPU.
    Only one of _txt/_img should be resident at a time on 8GB (they aren't
    both used in the same run)."""
    global _img
    if _img is None:
        import torch
        from diffusers import StableDiffusionXLImg2ImgPipeline

        cuda = torch.cuda.is_available()
        _img = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            config.IMAGE_MODEL_ID,
            torch_dtype=torch.float16 if cuda else torch.float32,
            variant="fp16" if cuda else None, use_safetensors=True,
        )
        if cuda:
            _img.enable_model_cpu_offload(); _img.enable_vae_slicing()
        else:
            _img.to("cpu")
    return _img


def product_shot(garment: str, color: str = "", details: str = "",
                 seed: int | None = 7) -> bytes:
    """txt2img product shot from attributes -> PNG bytes."""
    import torch

    pipe = _txt_pipe()
    gen = torch.Generator("cpu").manual_seed(seed) if seed is not None else None
    img = pipe(prompt=build_prompt(garment, color, details),
               negative_prompt=NEGATIVE, generator=gen, **PARAMS).images[0]
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()


def product_shot_from_ref(cutout_bytes: bytes, garment: str, color: str = "",
                          details: str = "", strength: float = 0.75,
                          seed: int | None = 7) -> bytes:
    """img2img: idealize a garment cutout into the steady product format.
    Higher strength -> cleaner/flatter but less faithful to the exact cutout."""
    import torch
    from PIL import Image

    # flatten transparent cutout onto white, square it, size for SDXL
    im = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(bg, im).convert("RGB")
    side = max(im.size)
    sq = Image.new("RGB", (side, side), (255, 255, 255))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    init = sq.resize((1024, 1024), Image.LANCZOS)

    pipe = _img_pipe()
    gen = torch.Generator("cpu").manual_seed(seed) if seed is not None else None
    img = pipe(prompt=build_prompt(garment, color, details), negative_prompt=NEGATIVE,
               image=init, strength=strength,
               num_inference_steps=PARAMS["num_inference_steps"],
               guidance_scale=PARAMS["guidance_scale"], generator=gen).images[0]
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()
