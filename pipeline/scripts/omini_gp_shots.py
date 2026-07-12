"""OminiControl via the GPU-poor fork (mmgp) — image-conditioned product shots.

The vanilla repo's custom forwards + GGUF weights deadlocked (0 steps in 20
min). This follows deepbeepmeep/OminiControlGP's documented 8GB recipe
exactly: full bf16 schnell + subject LoRA, then mmgp offload.profile(4)
(async weight streaming + smart placement; ~9s/img claimed on 8GB).

Weights all come from the non-gated mirror; the SAM2 cutouts on white are the
subject conditions; prompts come from the v2.2 archetype descriptions.

Usage:
  python pipeline/scripts/omini_gp_shots.py b2_r1c4
"""
from __future__ import annotations

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
sys.path.insert(0, str(ROOT / "vendor" / "OminiControlGP"))

OUT = ROOT / "review" / "garments_omini"
CONDS = OUT / "conditions"
SHOTS = OUT / "shots"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
BASE_REPO = "YuCollection/FLUX.1-schnell-Diffusers"

STEM = next((a for a in sys.argv[1:] if not a.startswith("--")), "b2_r1c4")
PROFILE = int(os.environ.get("MMGP_PROFILE", "4"))  # 4 = the 8GB recipe


def _strip_hex(s: str) -> str:
    return re.sub(r"\s*\(?~?#?[0-9a-fA-F]{6}\)?", "", s).replace("()", "").strip()


def build_prompt(g: dict) -> str:
    core = _strip_hex(g.get("prompt") or f"{g.get('color','')} {g.get('item','')}").strip(" ,.")
    return (f"professional e-commerce catalog product photograph of this exact item: {core}. "
            f"The item is shown alone, laid out neatly, centered on a pure seamless white "
            f"background, soft even studio lighting, sharp focus, true to the reference "
            f"item's real color, shape, proportions and material. No person, no body, "
            f"no mannequin, no props, no text.")


def main() -> None:
    # NOTE: mmgp is imported AFTER the pipeline loads — importing it patches
    # safetensors loading globally and its patch predates transformers 5.x
    # ('_SafeTensorLoader' has no 'keys'). Vanilla load first, then profile.
    from diffusers.pipelines import FluxPipeline
    from src.flux.condition import Condition
    from src.flux.generate import generate, seed_everything

    garments = json.loads((DESCS / f"{STEM}.json").read_text(encoding="utf-8"))
    jobs = []
    for i, g in enumerate(garments):
        cond_file = CONDS / f"{STEM}_{i}_{g.get('category','x')}.png"
        if cond_file.exists():
            jobs.append((i, g, cond_file))
    print(f"{STEM}: {len(jobs)} garments with condition images", flush=True)
    if not jobs:
        sys.exit("no condition images")

    t0 = time.time()
    print("loading bf16 pipeline (CPU)...", flush=True)
    pipe = FluxPipeline.from_pretrained(BASE_REPO, torch_dtype=torch.bfloat16)
    pipe.load_lora_weights(
        "Yuanshi/OminiControl",
        weight_name="omini/subject_512.safetensors",
        adapter_name="subject")
    print(f"pipeline + subject LoRA loaded in {time.time()-t0:.0f}s", flush=True)
    from mmgp import offload  # deferred import (see NOTE above)
    # profile 4 + bf16 streaming OOM'd our 8GB (desktop eats ~0.5GB);
    # int8-quantized transformer + profile 5 is the safe-margin recipe.
    offload.profile(pipe, profile_no=PROFILE, verboseLevel=1, quantizeTransformer=True)
    print(f"mmgp profile {PROFILE} applied (int8 transformer)", flush=True)

    SHOTS.mkdir(parents=True, exist_ok=True)
    for idx, g, cond_file in jobs:
        label = f"{g.get('color','')} {g.get('item','')}".strip()
        cond_img = Image.open(cond_file).convert("RGB").resize((512, 512))
        condition = Condition("subject", cond_img, position_delta=(0, 32))
        t = time.time()
        torch.cuda.reset_peak_memory_stats()
        seed_everything(42)
        img = generate(
            pipe,
            prompt=build_prompt(g),
            conditions=[condition],
            num_inference_steps=8,
            height=512, width=512,
        ).images[0]
        out = SHOTS / f"{STEM}_{idx}_{g.get('category','item')}.png"
        img.save(out)
        print(f"  [{idx}] {label}: {time.time()-t:.0f}s, "
              f"peak {torch.cuda.max_memory_allocated()/1e9:.1f}GB -> {out.name}", flush=True)

    print("OMINI-GP DONE", flush=True)


if __name__ == "__main__":
    main()
