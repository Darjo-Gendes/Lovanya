"""RunPod serverless entrypoint (architecture-decisions.md: scale-to-zero GPU).

Event shape:  {"input": {"op": "analyze"|"identify", "payload": {...}}}
The `runpod` import is optional so the same `handler` is unit-testable locally.
"""
from __future__ import annotations

import base64
from typing import Optional

from .app.contracts import AnalyzeRequest, IdentifyRequest
from .app.pipeline import PipelineError, run_analyze, run_identify


def _decode(b64: Optional[str]) -> Optional[bytes]:
    if not b64:
        return None
    data = b64.split(",", 1)[1] if b64.startswith("data:") else b64
    return base64.b64decode(data)


def handler(event: dict) -> dict:
    inp = (event or {}).get("input", {}) or {}
    op = inp.get("op")
    payload = inp.get("payload", {}) or {}
    try:
        if op == "identify":
            req = IdentifyRequest(**payload)
            return run_identify(_decode(req.photo_base64), req.palette, req.modestDefault).model_dump()
        if op == "analyze":
            req = AnalyzeRequest(**payload)
            return run_analyze(_decode(req.photo_base64), req.palette, req).model_dump()
        return {"error": f"unknown op {op!r} (expected 'identify' or 'analyze')"}
    except PipelineError as e:
        return {"error": str(e)}


if __name__ == "__main__":  # pragma: no cover
    try:
        import runpod  # type: ignore

        runpod.serverless.start({"handler": handler})
    except ImportError:
        print("runpod not installed — handler() is importable for local testing.")
