"""OminiControl subject-driven product shots — the image-conditioned path.

Text-only FLUX proved it ignores geometry words (portrait bag despite
"landscape, wider than tall"). OminiControl injects the actual garment PIXELS
(SAM2 cutout on white) as condition tokens into the same schnell we already
run, so color/shape/material come from the reference, not the prior.
+0.1% params (50MB LoRA), Apache-friendly base, ICCV'25.

8GB plan (proven pattern from the Qwen bench): phase A encodes all prompts via
a TE-only pipeline (model-cpu-offload juggles the 9.5GB T5), then dies; phase
B runs GGUF transformer + subject LoRA + VAE fully GPU-resident at 512px and
calls the repo's generate() with precomputed embeds.

Usage:
  python pipeline/scripts/omini_shots.py b2_r1c4
"""
from __future__ import annotations

import gc
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor" / "OminiControl"))
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "review" / "garments_omini"
CONDS = OUT / "conditions"
SHOTS = OUT / "shots"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
BASE_REPO = "YuCollection/FLUX.1-schnell-Diffusers"
LORA_REPO = "Yuanshi/OminiControl"
LORA_FILE = "omini/subject_512.safetensors"

STEM = next((a for a in sys.argv[1:] if not a.startswith("--")), "b2_r1c4")


def _strip_hex(s: str) -> str:
    return re.sub(r"\s*\(?~?#?[0-9a-fA-F]{6}\)?", "", s).replace("()", "").strip()


def build_prompt(g: dict) -> str:
    core = _strip_hex(g.get("prompt") or f"{g.get('color','')} {g.get('item','')}").strip(" ,.")
    return (f"professional e-commerce catalog product photograph of this exact item: {core}. "
            f"The item is shown alone, laid out neatly, centered on a pure seamless white "
            f"background, soft even studio lighting, sharp focus, true to the reference "
            f"item's real color, shape, proportions and material. No person, no body, "
            f"no mannequin, no props, no text.")


def find_gguf() -> Path:
    from huggingface_hub import scan_cache_dir
    for repo in scan_cache_dir().repos:
        if repo.repo_id == "city96/FLUX.1-schnell-gguf":
            for rev in repo.revisions:
                for f in rev.files:
                    if f.file_name.endswith(".gguf"):
                        return Path(f.file_path)
    raise SystemExit("FLUX GGUF not cached")


def encode_prompts(prompts: list[str]) -> list[tuple]:
    """Phase A: TE-only pipeline (offloaded), embeds to CPU, then destroyed."""
    from diffusers import FluxPipeline
    pipe = FluxPipeline.from_pretrained(
        BASE_REPO, transformer=None, vae=None, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    out = []
    with torch.inference_mode():
        for p in prompts:
            pe, ppe, _ = pipe.encode_prompt(prompt=p, prompt_2=None, device="cuda",
                                            max_sequence_length=512)
            out.append((pe.cpu(), ppe.cpu()))
            print(f"  encoded: {p[:60]}...", flush=True)
    del pipe
    gc.collect()
    torch.cuda.empty_cache()
    print(f"phase A done, vram={torch.cuda.memory_allocated()/1e9:.2f}GB", flush=True)
    return out


def build_generator():
    """Phase B: GGUF transformer + subject LoRA + VAE, GPU-resident, no TEs."""
    from diffusers import (FluxPipeline, FluxTransformer2DModel,
                           GGUFQuantizationConfig)
    gguf = find_gguf()
    print(f"transformer: {gguf.name}", flush=True)
    transformer = FluxTransformer2DModel.from_single_file(
        str(gguf),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        config=BASE_REPO, subfolder="transformer", torch_dtype=torch.bfloat16)
    pipe = FluxPipeline.from_pretrained(
        BASE_REPO, transformer=transformer,
        text_encoder=None, text_encoder_2=None,
        torch_dtype=torch.bfloat16)
    pipe.load_lora_weights(LORA_REPO, weight_name=LORA_FILE, adapter_name="subject")
    print("subject LoRA loaded", flush=True)
    pipe.transformer.to("cuda")
    pipe.vae.to("cuda")
    print(f"phase B resident, vram={torch.cuda.memory_allocated()/1e9:.2f}GB", flush=True)
    return pipe


def main() -> None:
    garments = json.loads((DESCS / f"{STEM}.json").read_text(encoding="utf-8"))
    jobs = []
    for i, g in enumerate(garments):
        cond_file = CONDS / f"{STEM}_{i}_{g.get('category','x')}.png"
        if cond_file.exists():
            jobs.append((i, g, cond_file))
    print(f"{STEM}: {len(jobs)} garments with condition images", flush=True)
    if not jobs:
        sys.exit("no condition images - run the SAM2 cutout step first")

    embeds = encode_prompts([build_prompt(g) for _, g, _ in jobs])

    from omini.pipeline.flux_omini import Condition, generate, seed_everything
    pipe = build_generator()
    SHOTS.mkdir(parents=True, exist_ok=True)

    for (idx, g, cond_file), (pe, ppe) in zip(jobs, embeds):
        label = f"{g.get('color','')} {g.get('item','')}".strip()
        cond_img = Image.open(cond_file).convert("RGB").resize((512, 512))
        condition = Condition(cond_img, "subject", position_delta=(0, 32))
        t = time.time()
        torch.cuda.reset_peak_memory_stats()
        seed_everything(42)
        img = generate(
            pipe,
            prompt_embeds=pe.to("cuda"),
            pooled_prompt_embeds=ppe.to("cuda"),
            conditions=[condition],
            num_inference_steps=8,
            height=512, width=512,
        ).images[0]
        out = SHOTS / f"{STEM}_{idx}_{g.get('category','item')}.png"
        img.save(out)
        print(f"  [{idx}] {label}: {time.time()-t:.0f}s, "
              f"peak {torch.cuda.max_memory_allocated()/1e9:.1f}GB -> {out.name}", flush=True)

    print("OMINI DONE", flush=True)


if __name__ == "__main__":
    main()
