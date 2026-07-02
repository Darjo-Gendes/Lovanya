"""Single source of truth for the swappable boundaries.

Per architecture-decisions.md: the model identifier lives in ONE constant so
swapping the judgment model (honest-mock -> Qwen2.5-VL -> a stronger model) is a
one-line change, never a code rewrite.
"""
from __future__ import annotations

import os

# --- Swappable model boundary -------------------------------------------------
# "honest-mock"   : GPU-free analyzer that reuses the app's real colour logic.
# "qwen2.5-vl-3b" : the planned default VLM (not wired yet — see app/analyze.py).
# "qwen2.5-vl-7b" : documented heavier fallback.
MODEL: str = os.environ.get("LOVANYA_MODEL", "honest-mock")

# --- Framework-as-file (the moat lives in text, not code) ---------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK_PATH: str = os.environ.get(
    "LOVANYA_FRAMEWORK", os.path.join(_HERE, "framework", "styling-framework.md")
)

# --- Output logging -----------------------------------------------------------
LOG_DIR: str = os.environ.get("LOVANYA_LOG_DIR", os.path.join(_HERE, "logs"))

# --- Boundaries / limits ------------------------------------------------------
MAX_IMAGE_BYTES: int = int(os.environ.get("LOVANYA_MAX_IMAGE_BYTES", 12 * 1024 * 1024))

# Origins allowed to call the HTTP service (the Next.js dev server by default).
CORS_ORIGINS: list[str] = os.environ.get(
    "LOVANYA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
