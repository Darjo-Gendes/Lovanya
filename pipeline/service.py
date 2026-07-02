"""HTTP surface for the pipeline — the contract the Next.js app calls.

  GET  /health          -> {status, model}
  POST /identify        -> ItemDraft        (add an item from a photo/palette)
  POST /analyze         -> OutfitAnalysis   (outfit check)

Run from the repo root:  uvicorn pipeline.service:app --port 8000 --reload
"""
from __future__ import annotations

import base64
import binascii
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .app.contracts import (
    AnalyzeRequest,
    IdentifyRequest,
    ItemDraftOut,
    OutfitAnalysisOut,
)
from .app.pipeline import PipelineError, run_analyze, run_identify

app = FastAPI(title="Lovanya Pipeline", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _decode_photo(b64: Optional[str]) -> Optional[bytes]:
    if not b64:
        return None
    data = b64.split(",", 1)[1] if b64.startswith("data:") else b64
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="photo_base64 is not valid base64.")
    if len(raw) > config.MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image exceeds size limit.")
    return raw


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": config.MODEL}


@app.post("/identify", response_model=ItemDraftOut)
def identify(req: IdentifyRequest) -> ItemDraftOut:
    image = _decode_photo(req.photo_base64)
    try:
        return run_identify(image, req.palette, req.modestDefault)
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/analyze", response_model=OutfitAnalysisOut)
def analyze(req: AnalyzeRequest) -> OutfitAnalysisOut:
    image = _decode_photo(req.photo_base64)
    try:
        return run_analyze(image, req.palette, req)
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))
