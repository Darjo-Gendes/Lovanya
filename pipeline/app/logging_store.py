"""Build seam — output logging.

Every judgment logs its input and output so quality can be pressure-tested
against real cases instead of re-generating them (architecture-decisions.md,
build seam #2). Append-only JSONL; never raises into the request path.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from .. import config


def log_judgment(kind: str, model: str, inp: Any, out: Any) -> None:
    """Append one {ts, kind, model, input, output} record to logs/judgments.jsonl."""
    try:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "kind": kind,
            "model": model,
            "input": _plain(inp),
            "output": _plain(out),
        }
        with open(os.path.join(config.LOG_DIR, "judgments.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never break the pipeline.
        pass


def _plain(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj
