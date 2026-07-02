import json
import shutil
import tempfile
import time
from pathlib import Path

from pydantic import BaseModel

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .analyze import analyze, get_analyzer

PIPELINE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = PIPELINE_DIR / "samples"
STATIC_DIR = Path(__file__).resolve().parent / "static"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

app = FastAPI(title="Lovanya AI Pipeline")

# Local dev tool: the test bench may be opened from file:// or a preview
# panel, and the Next.js app will call from another port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    try:
        import torch

        cuda = torch.cuda.is_available()
    except ImportError:
        cuda = False
    return {
        "status": "ok",
        "model": config.MODEL,
        "model_id": config.QWEN_MODEL_ID,
        "cuda": cuda,
        "model_loaded": _model_loaded(),
    }


def _model_loaded() -> bool:
    from . import analyze as analyze_module

    return analyze_module._analyzer is not None


@app.post("/warmup")
def warmup():
    """Load the model into VRAM ahead of the first analyze call."""
    t0 = time.time()
    get_analyzer()
    return {"loaded": True, "seconds": round(time.time() - t0, 1)}


@app.get("/api/samples")
def list_samples():
    if not SAMPLES_DIR.exists():
        return {"samples": []}
    names = sorted(
        p.name for p in SAMPLES_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTS
    )
    return {"samples": names}


@app.post("/api/analyze")
async def analyze_endpoint(
    occasion: str = Form("casual"),
    sample: str | None = Form(None),
    photo: UploadFile | None = File(None),
):
    if sample:
        image_path = SAMPLES_DIR / Path(sample).name
        if not image_path.exists():
            raise HTTPException(404, f"Sample not found: {sample}")
        image_path = str(image_path)
    elif photo:
        suffix = Path(photo.filename or "upload.jpg").suffix or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(photo.file, tmp)
            image_path = tmp.name
    else:
        raise HTTPException(422, "Provide either 'sample' or 'photo'")

    t0 = time.time()
    result = analyze(image_path, occasion)
    result["elapsed_seconds"] = round(time.time() - t0, 1)
    return result


class Rating(BaseModel):
    judgment_id: str
    rating: str  # "up" | "down"
    correction: str | None = None


@app.post("/api/rate")
def rate(r: Rating):
    """Store a user rating/correction — this is the training-data intake."""
    if r.rating not in ("up", "down"):
        raise HTTPException(422, "rating must be 'up' or 'down'")
    data_dir = PIPELINE_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    entry = {
        "rated_at": time.time(),
        "judgment_id": r.judgment_id,
        "rating": r.rating,
        "correction": r.correction or None,
    }
    with open(data_dir / "ratings.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"saved": True}


app.mount("/samples", StaticFiles(directory=str(SAMPLES_DIR)), name="samples")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
