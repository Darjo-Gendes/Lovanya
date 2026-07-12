"""Fetch FLUX.1 [schnell] for the local describe->generate pipeline.

schnell is Apache-2.0 (commercial-safe, unlike dev) and 4-step. On the 8GB
card we run the GGUF transformer + the base repo's T5/CLIP/VAE via diffusers
model-cpu-offload. Resumable through the HF cache; Xet disabled (it stalls on
this network).

  ~7GB  transformer  city96/FLUX.1-schnell-gguf  (Q4_K_S — best 8GB fit)
 ~10GB  T5 + CLIP + VAE + configs  black-forest-labs/FLUX.1-schnell
"""
from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download

GGUF_REPO = "city96/FLUX.1-schnell-gguf"
# BFL gated the official schnell repo (401 even though it's Apache-2.0); this
# is a non-gated diffusers-format mirror of the same weights. Transformer
# comes from the GGUF above, so we skip its safetensors here.
BASE_REPO = "YuCollection/FLUX.1-schnell-Diffusers"
QUANT_PREF = ["Q4_K_S", "Q4_K_M", "Q3_K_S", "Q5_K_S"]


def main() -> None:
    files = list_repo_files(GGUF_REPO)
    ggufs = [f for f in files if f.endswith(".gguf")]
    pick = next((f for q in QUANT_PREF for f in ggufs if q in f), None)
    if not pick:
        raise SystemExit(f"no usable quant in {GGUF_REPO}: {ggufs}")
    print(f"[1/2] transformer {pick} from {GGUF_REPO}", flush=True)
    print("      ->", hf_hub_download(GGUF_REPO, pick), flush=True)

    print(f"[2/2] T5 + CLIP + VAE + configs from {BASE_REPO}", flush=True)
    base = snapshot_download(
        BASE_REPO,
        allow_patterns=[
            "model_index.json", "scheduler/*", "vae/*",
            "tokenizer/*", "tokenizer_2/*",
            "text_encoder/*", "text_encoder_2/*",
            "transformer/config.json",  # GGUF loader needs the arch config
        ],
    )
    print("      ->", base, flush=True)
    print("DOWNLOAD COMPLETE", flush=True)


if __name__ == "__main__":
    main()
