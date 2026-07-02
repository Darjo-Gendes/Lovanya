import os

MODEL = os.environ.get("MODEL", "qwen")

QWEN_MODEL_ID = os.environ.get("QWEN_MODEL_ID", "Qwen/Qwen2.5-VL-3B-Instruct")

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
