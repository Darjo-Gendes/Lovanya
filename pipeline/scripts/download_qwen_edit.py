"""Fetch Qwen-Image-Edit for the local vs Nano Banana benchmark (~25 GB).

Pieces (all resumable via the HF cache):
- transformer: GGUF quant from QuantStack (Q3_K_M — the 8GB card streams the
  weights per-step under sequential offload, so quant size ~= step latency)
- everything else (text encoder, VAE, tokenizer, scheduler): official repo
- Lightning 8-step LoRA: optional, cuts steps 20 -> 8 if it loads on GGUF
"""
from __future__ import annotations

from huggingface_hub import hf_hub_download, list_repo_files, snapshot_download

GGUF_REPO = "QuantStack/Qwen-Image-Edit-GGUF"
BASE_REPO = "Qwen/Qwen-Image-Edit"
LORA_REPO = "lightx2v/Qwen-Image-Lightning"
QUANT_PREF = ["Q3_K_M", "Q3_K_S", "Q4_K_M", "Q4_0", "Q2_K"]


def main() -> None:
    files = list_repo_files(GGUF_REPO)
    ggufs = [f for f in files if f.endswith(".gguf")]
    pick = next((f for q in QUANT_PREF for f in ggufs if q in f), None)
    if not pick:
        raise SystemExit(f"no usable quant in {GGUF_REPO}: {ggufs}")
    print(f"[1/3] transformer {pick} from {GGUF_REPO}", flush=True)
    gguf_path = hf_hub_download(GGUF_REPO, pick)
    print("      ->", gguf_path, flush=True)

    print(f"[2/3] base components from {BASE_REPO} (text encoder is ~16GB)", flush=True)
    base = snapshot_download(
        BASE_REPO,
        allow_patterns=["model_index.json", "scheduler/*", "tokenizer/*",
                        "processor/*", "text_encoder/*", "vae/*"],
    )
    print("      ->", base, flush=True)

    print(f"[3/3] Lightning LoRA from {LORA_REPO} (optional)", flush=True)
    try:
        loras = [f for f in list_repo_files(LORA_REPO) if f.endswith(".safetensors")
                 and "Edit" in f and "8step" in f]
        lora = sorted(loras)[-1] if loras else None
        if lora:
            print("      ->", hf_hub_download(LORA_REPO, lora), flush=True)
        else:
            print("      no edit-specific 8-step LoRA found, benchmark uses 20 steps", flush=True)
    except Exception as e:  # LoRA is a speed bonus, never a blocker
        print("      skipped:", e, flush=True)
    print("DOWNLOAD COMPLETE", flush=True)


if __name__ == "__main__":
    main()
