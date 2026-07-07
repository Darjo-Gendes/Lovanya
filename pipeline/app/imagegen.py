"""Local render engine — turn a garment cutout into a clean product shot.

Open-weight, on-GPU, zero tokens (SDXL img2img via diffusers on the RTX 4060
Ti). This is the render stage of the pipeline (see render.py); it is NOT a
LookCard generator — LookCards stay deterministic DOM per visual-pipeline-v1.md.
"Nano Banana" (Google Gemini 2.5 Flash Image) is a paid cloud API and cannot
run here; SDXL is the free local, commercial-usable stand-in.

Fits 8GB VRAM via model-cpu-offload + VAE slicing. Co-residency guardrail
(comfyui-flux-setup.md): the Qwen judge and this model must NOT both be
resident on 8GB — render() runs after analyze(), so free the judge first.
"""
from __future__ import annotations

import io

from .. import config

_pipe = None

PROMPT = (
    "professional e-commerce product photograph of {desc}, laid flat / ghost-"
    "mannequin catalogue style, pure seamless white background, centered, soft "
    "even studio lighting, sharp focus, high detail, true colors"
)
NEGATIVE = (
    "person, face, hands, mannequin head, busy background, shadow clutter, "
    "lowres, blurry, deformed, watermark, text, logo, extra garment"
)


def _get_pipe():
    global _pipe
    if _pipe is None:
        import torch
        from diffusers import StableDiffusionXLImg2ImgPipeline

        cuda = torch.cuda.is_available()
        _pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            config.IMAGE_MODEL_ID,
            torch_dtype=torch.float16 if cuda else torch.float32,
            variant="fp16" if cuda else None,
            use_safetensors=True,
        )
        if cuda:
            _pipe.enable_model_cpu_offload()
            _pipe.enable_vae_slicing()
        else:
            _pipe.to("cpu")
    return _pipe


def _prep(image_bytes: bytes, size: int = 1024):
    """Cutout bytes -> RGB square on white, sized for SDXL. Transparent areas
    (from SAM2/BiRefNet) are flattened to white so the model cleans, not
    invents, the background."""
    from PIL import Image

    im = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(bg, im).convert("RGB")
    # pad to square then resize, so aspect isn't distorted
    w, h = im.size
    side = max(w, h)
    square = Image.new("RGB", (side, side), (255, 255, 255))
    square.paste(im, ((side - w) // 2, (side - h) // 2))
    return square.resize((size, size), Image.LANCZOS)


def render_product_shot(image_bytes: bytes, garment_desc: str = "a clothing garment",
                        strength: float = 0.4, steps: int = 30, seed: int | None = None) -> bytes:
    """Garment cutout bytes -> clean product-shot PNG bytes. Higher strength =
    more standardized but less faithful to the original garment."""
    import torch

    pipe = _get_pipe()
    init = _prep(image_bytes)
    generator = torch.Generator(device="cpu").manual_seed(seed) if seed is not None else None
    image = pipe(
        prompt=PROMPT.format(desc=garment_desc),
        negative_prompt=NEGATIVE,
        image=init, strength=strength,
        num_inference_steps=steps, guidance_scale=6.0,
        generator=generator,
    ).images[0]
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
