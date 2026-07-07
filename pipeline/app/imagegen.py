"""Local outfit / LookCard image generation — open-weight, on-GPU, zero tokens.

Uses SDXL via diffusers on the RTX 4060 Ti. No cloud, no API, no per-image
cost (unlike "Nano Banana" = Google Gemini 2.5 Flash Image, which is a paid
cloud API and cannot run locally).

Fits 8GB VRAM via model-cpu-offload + VAE slicing. One generator is cached
per process; each call is an independent one-shot generation.

The prompt is built from outfit data (occasion + garment description), so the
same perception the judge produces can drive the visual.
"""
from __future__ import annotations

import os

from .. import config

_pipe = None

# Editorial-lookbook framing so outputs read as fashion cards, not random art.
STYLE_PREFIX = (
    "full-body fashion lookbook photograph, single female model, "
    "clean studio backdrop, soft even lighting, sharp focus, editorial styling"
)
NEGATIVE = (
    "lowres, blurry, deformed, extra limbs, extra fingers, bad anatomy, "
    "watermark, text, logo, cluttered background, nsfw"
)


def _get_pipe():
    global _pipe
    if _pipe is None:
        import torch
        from diffusers import StableDiffusionXLPipeline

        cuda = torch.cuda.is_available()
        _pipe = StableDiffusionXLPipeline.from_pretrained(
            config.IMAGE_MODEL_ID,
            torch_dtype=torch.float16 if cuda else torch.float32,
            variant="fp16" if cuda else None,
            use_safetensors=True,
        )
        if cuda:
            # keep 8GB happy: stream modules to GPU as needed + slice VAE
            _pipe.enable_model_cpu_offload()
            _pipe.enable_vae_slicing()
        else:
            _pipe.to("cpu")
    return _pipe


def build_prompt(occasion: str, garment_desc: str, palette: list[str] | None = None) -> str:
    """Compose an SDXL prompt from outfit data (occasion + garments + colors)."""
    colors = ", ".join(palette[:3]) if palette else ""
    bits = [STYLE_PREFIX, f"wearing {garment_desc}"]
    if colors:
        bits.append(f"color palette {colors}")
    bits.append(f"styled for {occasion}")
    return ", ".join(bits)


def generate(occasion: str, garment_desc: str, palette: list[str] | None = None,
             out_path: str | None = None, steps: int = 28, seed: int | None = None):
    """Generate one outfit/LookCard image. Returns the saved file path."""
    import torch

    pipe = _get_pipe()
    prompt = build_prompt(occasion, garment_desc, palette)
    generator = None
    if seed is not None:
        generator = torch.Generator(device="cpu").manual_seed(seed)
    image = pipe(
        prompt=prompt, negative_prompt=NEGATIVE,
        num_inference_steps=steps, guidance_scale=6.5,
        width=832, height=1216,  # portrait, LookCard aspect
        generator=generator,
    ).images[0]

    if out_path is None:
        out_dir = os.path.join(config.DATA_DIR, "lookcards")
        os.makedirs(out_dir, exist_ok=True)
        stem = "".join(c for c in occasion if c.isalnum())[:20] or "look"
        out_path = os.path.join(out_dir, f"{stem}_{seed if seed is not None else 'rand'}.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    image.save(out_path)
    return out_path
