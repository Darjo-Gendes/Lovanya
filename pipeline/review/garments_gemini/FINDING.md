# Finding: local Qwen-Image-Edit cannot do garment extraction on the 8GB card

**Date:** 2026-07-11 · **Hardware:** RTX 4060 Ti 8GB, 32GB RAM
**Task:** worn outfit photo → Uniqlo-style flat product shot per garment
(b2_r1c4, identical prompts to the Nano Banana run, seed 42).

## Result

| Config | Time/image | Peak VRAM | Output |
|---|---|---|---|
| Q3_K_M GGUF + Lightning 8-step, cfg 1.0 | 74s | 4.7GB | **input photo reproduced** — no extraction |
| Q3_K_M GGUF, 20 steps, true-CFG 4.0 + negative | 316s | 4.7GB | **same identity-copy failure** |
| Nano Banana (Gemini, AI Studio) | ~12s | — | correct catalog-grade flat shots (user-verified) |

Outputs preserved in `local_qwen_lightning/` and `local_qwen/`.

## Why it fails here

The 8GB card forces three compromises the official recipe doesn't make:
Q3_K_M weight quantization, a 512² VL condition view (the 7B text encoder's
vision tower OOMs at the official ~1MP view), and streamed weights. The model
answers with near-verbatim reconstructions of the conditioning image; raising
CFG to 4 with a negative prompt does not break the identity behaviour. The
configuration that plausibly works (bf16/fp8, 1MP condition view, 24GB+ VRAM)
does not exist on this machine.

## Hard-won engineering notes (for any future GGUF diffusion work)

1. `enable_sequential_cpu_offload()` **corrupts GGUF params** — accelerate's
   meta-device round trip drops `quant_type` → `GGML_QUANT_SIZES[None]`.
   Use `diffusers.hooks.apply_group_offloading(..., offload_type="leaf_level",
   use_stream=True)` instead (0.26GB resident, ~9s/step for a 20B model).
2. diffusers takes `torch_dtype=`, not `dtype=` — the latter is silently
   ignored and the VAE loads fp32 (conv3d dtype crash).
3. A direct `pipe.encode_prompt()` call is **not** under `@torch.no_grad()` —
   wrap in `torch.inference_mode()` or every VL forward retains its autograd
   graph (21GB "allocated" after two encodes via WDDM spill).
4. NF4-quantized Qwen2.5-VL-7B is 6.25GB on GPU, not ~4.5 — bitsandbytes only
   quantizes Linear layers; vision tower + embeddings stay bf16.
5. Phase isolation works: encode all prompts first (TE-only pipeline),
   destroy it, then build the denoiser with `text_encoder=None` and feed
   `prompt_embeds` (mask legitimately comes back `None` when unpadded).
6. HF Xet downloads can stall at 0 bytes on this network — set
   `HF_HUB_DISABLE_XET=1` (plain HTTP ran at full line speed).

## Decision

Cloud Nano Banana stays the product-shot engine (config
`LOVANYA_PRODUCT_BACKEND=gemini`). Local generation remains fallback-only for
non-extraction tasks (SDXL idealized txt2img). The blocked item is billing on
the Gemini key: free tier has **0 image-gen quota** (all models 429) —
enabling billing unlocks the 20-outfit batch for ~$4-7.
