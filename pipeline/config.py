"""Single source of truth for the swappable boundaries.

Per architecture-decisions.md: the model identifier lives in ONE constant so
swapping the judgment model (honest-mock -> Qwen2.5-VL -> a stronger model) is a
one-line change, never a code rewrite.
"""
from __future__ import annotations

import os

# --- Swappable model boundary -------------------------------------------------
# "qwen"        : Qwen2.5-VL judging the actual photo (needs the GPU box).
# "honest-mock" : GPU-free analyzer that reuses the app's real colour logic —
#                 set LOVANYA_MODEL=honest-mock on machines without the GPU.
# Any value starting with "qwen" selects the Qwen analyzer; the exact weights
# come from QWEN_MODEL_ID. `MODEL` is accepted as a legacy alias for the env var.
MODEL: str = os.environ.get("LOVANYA_MODEL") or os.environ.get("MODEL") or "qwen"

# Hugging Face id of the Qwen weights. Qwen3-VL-8B replaced Qwen2.5-VL-3B on
# the GPU box (2026-07-02): generational quality jump, and NF4-quantized it
# fits the 8GB card fully instead of spilling to CPU.
QWEN_MODEL_ID: str = os.environ.get("QWEN_MODEL_ID", "Qwen/Qwen3-VL-8B-Instruct")

# "4bit" = quantize at load with bitsandbytes NF4 (how 8B fits in 8GB VRAM);
# "none" = the checkpoint's native precision. Prequantized AWQ/compressed-
# tensors checkpoints fail at inference on Windows+transformers-v5 — don't.
QUANT: str = os.environ.get("LOVANYA_QUANT", "4bit")

# "dino" = GroundingDINO garment detection before perception; "off" = whole image.
SEGMENT: str = os.environ.get("LOVANYA_SEGMENT", "dino")

# "1" = perceive+judge in ONE model call (~halves latency); "0" = two calls.
ONESHOT: bool = os.environ.get("LOVANYA_ONESHOT", "1") == "1"

# Trained LoRA adapter (scripts/train_qlora.py output): a path, "auto" to
# use the most recently modified dir under pipeline/adapters/ (so a finished
# training run is picked up by the next model load with no restart or
# config change), or "" to run the base model.
ADAPTER: str = os.environ.get("LOVANYA_ADAPTER", "auto")

# --- Local image generation (outfit / LookCard visuals) -----------------------
# Open-weight, on-GPU, zero tokens. Swap here to change the image model
# ("Nano Banana" = Google Gemini 2.5 Flash Image is cloud-only, not usable
# here). SDXL fits the 8GB card via cpu-offload.
IMAGE_MODEL_ID: str = os.environ.get(
    "LOVANYA_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0"
)
# "on" = render the optional clean product shot; "off" = skip it.
RENDER: str = os.environ.get("LOVANYA_RENDER", "on")

# --- Framework-as-file (the moat lives in text, not code) ---------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK_PATH: str = os.environ.get(
    "LOVANYA_FRAMEWORK", os.path.join(_HERE, "framework", "styling-framework.md")
)

# --- Output logging -----------------------------------------------------------
LOG_DIR: str = os.environ.get("LOVANYA_LOG_DIR", os.path.join(_HERE, "logs"))

# --- Training data (gold seed set + user ratings from the test bench) ---------
DATA_DIR: str = os.environ.get("LOVANYA_DATA_DIR", os.path.join(_HERE, "data"))

# --- Boundaries / limits ------------------------------------------------------
MAX_IMAGE_BYTES: int = int(os.environ.get("LOVANYA_MAX_IMAGE_BYTES", 12 * 1024 * 1024))

# Origins allowed to call the HTTP service (the Next.js dev server by default).
CORS_ORIGINS: list[str] = os.environ.get(
    "LOVANYA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
