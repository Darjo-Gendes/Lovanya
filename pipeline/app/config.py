import os

MODEL = os.environ.get("MODEL", "qwen")

QWEN_MODEL_ID = os.environ.get("QWEN_MODEL_ID", "Qwen/Qwen3-VL-8B-Instruct")

# "4bit" = bitsandbytes NF4 quantization at load (fits 8B in 8GB VRAM);
# "none" = checkpoint's native precision
QUANT = os.environ.get("QUANT", "4bit")

# "dino" = GroundingDINO garment-crop before perception; "off" = whole image
SEGMENT = os.environ.get("SEGMENT", "dino")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
)

FRAMEWORK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "framework",
    "styling-framework.md",
)

LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs",
    "judgments.jsonl",
)
