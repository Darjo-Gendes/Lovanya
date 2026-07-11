"""Local Qwen-Image-Edit vs Nano Banana: identical photo, identical prompts.

Runs the b2_r1c4 garments (from the cached Gemini analysis) through the GGUF
Qwen-Image-Edit on the 4060 Ti and saves to review/garments_gemini/local_qwen/
so the review page can show the strips side by side. Logs seconds + VRAM per
image — the benchmark is quality AND cost-of-quality.

8GB VRAM = strict phase isolation (nothing shares the card):
  A) text-encoder-only pipeline (NF4, small VL condition view) encodes every
     prompt, then the whole thing is destroyed;
  B) transformer(GGUF, group-offloaded leaf streaming) + VAE denoise from the
     saved embeds with text_encoder=None.
Hard-won gotchas: sequential offload corrupts GGUF params (meta-device round
trip drops quant_type); diffusers wants torch_dtype= not dtype=; the VL vision
tower OOMs at 1MP condition views (Edit-Plus uses a small view officially).
"""
from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gemini_shots import _shot_prompt, ANALYSIS, SAMPLES, SHOT_CATS  # noqa: E402

OUT = ROOT / "review" / "garments_gemini" / "local_qwen"
STEM = sys.argv[1] if len(sys.argv) > 1 else "b2_r1c4"
BASE = "Qwen/Qwen-Image-Edit"


def find_cached(repo_id: str, suffix: str) -> Path | None:
    from huggingface_hub import scan_cache_dir
    for repo in scan_cache_dir().repos:
        if repo.repo_id == repo_id:
            for rev in repo.revisions:
                for f in rev.files:
                    if f.file_name.endswith(suffix):
                        return Path(f.file_path)
    return None


def vram(tag: str) -> None:
    print(f"  vram[{tag}]: {torch.cuda.memory_allocated() / 1e9:.2f}GB", flush=True)


def encode_all(jobs: list, cond_small: Image.Image, need_negative: bool):
    """Phase A: TE-only pipeline -> embeds on CPU -> everything freed."""
    from diffusers import QwenImageEditPipeline
    from transformers import BitsAndBytesConfig, Qwen2_5_VLForConditionalGeneration

    te = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        BASE, subfolder="text_encoder", dtype=torch.bfloat16,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16),
    )
    pipe = QwenImageEditPipeline.from_pretrained(
        BASE, text_encoder=te, transformer=None, vae=None,
        torch_dtype=torch.bfloat16)
    vram("encoder loaded")

    embeds, neg = [], None
    # __call__ is @torch.no_grad() but a direct encode_prompt is NOT — without
    # this, every VL forward retains its autograd graph (21GB after 2 encodes).
    with torch.inference_mode():
        for idx, g in jobs:
            pe, pem = pipe.encode_prompt(
                prompt=_shot_prompt(g), image=cond_small, device="cuda")
            # mask comes back None by design when every token is valid
            embeds.append((pe.cpu(), pem.cpu() if pem is not None else None))
            print(f"  encoded [{idx}] {g.get('item', '')}", flush=True)
        if need_negative:
            npe, npem = pipe.encode_prompt(prompt=" ", image=cond_small, device="cuda")
            neg = (npe.cpu(), npem.cpu() if npem is not None else None)

    del pipe, te
    gc.collect()
    torch.cuda.empty_cache()
    vram("encoder freed")
    return embeds, neg


def build_denoiser(use_lora: bool):
    """Phase B: GGUF transformer (leaf-streamed) + VAE, no text encoder."""
    from diffusers import (GGUFQuantizationConfig, QwenImageEditPipeline,
                           QwenImageTransformer2DModel)
    from diffusers.hooks import apply_group_offloading

    gguf = find_cached("QuantStack/Qwen-Image-Edit-GGUF", ".gguf")
    if not gguf:
        raise SystemExit("GGUF not in cache - run download_qwen_edit.py first")
    print(f"transformer: {gguf.name}", flush=True)
    transformer = QwenImageTransformer2DModel.from_single_file(
        str(gguf),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        config=BASE, subfolder="transformer", dtype=torch.bfloat16,
    )
    pipe = QwenImageEditPipeline.from_pretrained(
        BASE, transformer=transformer, text_encoder=None, processor=None,
        torch_dtype=torch.bfloat16)

    steps, cfg = 20, 4.0
    lora = find_cached("lightx2v/Qwen-Image-Lightning", ".safetensors") if use_lora else None
    if lora:
        try:
            pipe.load_lora_weights(str(lora))
            steps, cfg = 8, 1.0
            print(f"lightning LoRA loaded ({lora.name}) -> {steps} steps", flush=True)
        except Exception as e:
            print(f"lightning LoRA failed ({e}) -> {steps} steps", flush=True)
    else:
        print(f"standard mode: {steps} steps, true_cfg {cfg}", flush=True)

    # Sequential offload is incompatible with GGUF params (accelerate's
    # meta-device round trip drops quant_type -> GGML_QUANT_SIZES[None]).
    apply_group_offloading(
        pipe.transformer,
        onload_device=torch.device("cuda"),
        offload_device=torch.device("cpu"),
        offload_type="leaf_level",
        use_stream=True,
    )
    pipe.vae.to("cuda")
    vram("denoiser ready")
    return pipe, steps, cfg


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    garments = json.loads((ANALYSIS / f"{STEM}.json").read_text(encoding="utf-8"))
    jobs = [(i, g) for i, g in enumerate(garments) if g.get("category") in SHOT_CATS]
    print(f"{STEM}: {len(jobs)} garments, device {torch.cuda.get_device_name(0)}", flush=True)

    # Mirror the pipeline's conditioning sizes without needing a pipeline yet:
    # full-res (area ~1MP, multiple of 16) for the VAE, small view for the VL
    # encoder (its full-attention layers OOM 8GB at 1MP; Edit-Plus does this).
    from diffusers.pipelines.qwenimage.pipeline_qwenimage_edit import calculate_dimensions
    src = Image.open(SAMPLES / f"{STEM}.jpg").convert("RGB")
    w, h, _ = calculate_dimensions(1024 * 1024, src.size[0] / src.size[1])
    w, h = w // 16 * 16, h // 16 * 16
    cond = src.resize((w, h), Image.LANCZOS)
    cw, ch, _ = calculate_dimensions(512 * 512, src.size[0] / src.size[1])
    cond_small = src.resize((cw, ch), Image.LANCZOS)

    import os
    # Lightning-8step at cfg=1.0 reproduced the input photo near-verbatim
    # (identity-preserving failure); QWEN_BENCH_NO_LORA=1 runs the standard
    # 20-step true-CFG-4 recipe the model card recommends for hard edits.
    use_lora = (os.environ.get("QWEN_BENCH_NO_LORA") != "1"
                and find_cached("lightx2v/Qwen-Image-Lightning", ".safetensors") is not None)

    t0 = time.time()
    embeds, neg = encode_all(jobs, cond_small, need_negative=not use_lora)
    print(f"phase A (encode) done in {time.time() - t0:.0f}s", flush=True)

    t0 = time.time()
    pipe, steps, cfg = build_denoiser(use_lora)
    if cfg > 1.0 and neg is None:
        cfg = 1.0  # safety net: never run true-CFG without negative embeds
    print(f"phase B pipeline ready in {time.time() - t0:.0f}s", flush=True)

    timings = []
    for (idx, g), (pe, pem) in zip(jobs, embeds):
        label = f"{g.get('color', '')} {g.get('item', '')}".strip()
        t = time.time()
        torch.cuda.reset_peak_memory_stats()
        extra = {}
        if neg is not None and cfg > 1.0:
            extra = {"negative_prompt_embeds": neg[0].to("cuda"),
                     "negative_prompt_embeds_mask":
                         neg[1].to("cuda") if neg[1] is not None else None}
        image = pipe(
            image=cond, prompt_embeds=pe.to("cuda"),
            prompt_embeds_mask=pem.to("cuda") if pem is not None else None,
            height=h, width=w, num_inference_steps=steps, true_cfg_scale=cfg,
            generator=torch.Generator("cpu").manual_seed(42), **extra,
        ).images[0]
        dt = time.time() - t
        peak = torch.cuda.max_memory_allocated() / 1e9
        out = OUT / f"{STEM}_{idx}_{g.get('category', 'item')}.png"
        image.save(out)
        timings.append(dt)
        print(f"  [{idx}] {label}: {dt:.0f}s, peak VRAM {peak:.1f}GB -> {out.name}", flush=True)

    print(f"BENCH DONE: {len(timings)} images, avg {sum(timings) / len(timings):.0f}s/image "
          f"({steps} steps). Nano Banana equivalent: ~10-15s/image, $0.039.", flush=True)


if __name__ == "__main__":
    main()
