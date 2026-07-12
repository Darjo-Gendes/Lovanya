"""Local FLUX.1 [schnell] product shots from garment descriptions.

The generate half of the describe->generate pipeline. Reads the garment
manifest (the same analysis/*.json the Gemini run produced, or a local
Qwen3-VL run) and renders each garment as a standalone product shot on the
4060 Ti — zero tokens, Apache-2.0 weights.

8GB strategy: GGUF transformer (from_single_file) + enable_model_cpu_offload,
which pages CLIP/T5/transformer/VAE on and off the card as each runs, so the
9.5GB T5 never has to co-reside with the 6.8GB transformer.

Prompt format defaults (user deferred the choice, 2026-07-11): flat-lay,
pure-white square, fidelity-weighted. Override via env without code edits:
  LOVANYA_FLUX_PRESENT = flatlay | ghost | hanging
  LOVANYA_FLUX_BG      = white | shadow
Usage:
  python pipeline/scripts/flux_shots.py b2_r1c4        # one sample
  python pipeline/scripts/flux_shots.py --review-only
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gemini_shots import ANALYSIS, SAMPLES, SHOT_CATS, OLD_SHOTS  # noqa: E402

OUT = ROOT / "review" / "garments_flux"
SHOTS = OUT / "shots"
DESC_DIR = OUT / "descriptions"  # local Qwen3-VL generation-first output
BASE_REPO = "YuCollection/FLUX.1-schnell-Diffusers"


def desc_path(stem: str) -> Path:
    """Prefer the new local generation-first descriptions; fall back to the
    Gemini analysis cache so old samples still render."""
    p = DESC_DIR / f"{stem}.json"
    return p if p.exists() else ANALYSIS / f"{stem}.json"


def desc_stems() -> list[str]:
    stems = {p.stem for p in DESC_DIR.glob("*.json")} if DESC_DIR.exists() else set()
    stems |= {p.stem for p in ANALYSIS.glob("*.json")}
    return sorted(stems)

PRESENT = os.environ.get("LOVANYA_FLUX_PRESENT", "flatlay")
BG = os.environ.get("LOVANYA_FLUX_BG", "white")
STEPS = int(os.environ.get("LOVANYA_FLUX_STEPS", "4"))
# 1024px peaked at 9.8GB on the 8GB card -> spilled to shared RAM -> 139s/step.
# 768px keeps the whole forward pass in VRAM; per-step drops back to seconds.
SIZE = int(os.environ.get("LOVANYA_FLUX_SIZE", "768"))

_POSE = {
    "flatlay": "laid perfectly flat and neatly arranged, photographed straight from directly above (top-down flat lay)",
    "ghost": "shown on an invisible ghost-mannequin holding its natural 3D shape, front view",
    "hanging": "displayed hanging neatly on a plain hanger, front view",
}
# bags/shoes: schnell ignores negatives, so assert "unworn, on a surface"
# POSITIVELY or FLUX drapes the bag on a mannequin torso (user: no mannequin).
_POSE_UPRIGHT = ("photographed entirely by itself as an isolated product, resting on a plain "
                 "flat surface, standing upright at a three-quarter front angle, the item alone "
                 "and completely unworn, not on any body, torso, mannequin or dress form")

# Worn-shape items (user 2026-07-11): hijab, necklace, earrings NEED a display
# form to show their worn drape/fall - featureless so it reads as product, not
# portrait. Everything else stays a standalone piece.
_MANNEQUIN_HEAD = ("styled as worn on a smooth featureless abstract white display mannequin "
                   "head with no facial features, neat elegant drape, front view")
_MANNEQUIN_BUST = ("displayed on a minimalist featureless white mannequin bust form, neck and "
                   "shoulders only with no face, jewelry-store presentation")
_MANNEQUIN_EAR = ("displayed on the ear of a smooth featureless white mannequin head with no "
                  "facial features, close-up three-quarter view")

_TAIL_STANDALONE = ("garment only, no person, no body, no face, no mannequin head, "
                    "no other clothing, no props, no text, no watermark")
_TAIL_MANNEQUIN = ("only the item and its plain display form, no human skin, no facial "
                   "features, no hair, no other clothing or jewelry, no props, no text, "
                   "no watermark")


def pick_pose(g: dict) -> tuple[str, str]:
    """-> (pose phrase, constraint tail) per category/item."""
    cat = g.get("category", "")
    item = f"{g.get('item','')} {g.get('type','')} {g.get('archetype','')}".lower()
    if cat == "hijab":
        return _MANNEQUIN_HEAD, _TAIL_MANNEQUIN
    if "necklace" in item or "pendant" in item or "chain" in item:
        return _MANNEQUIN_BUST, _TAIL_MANNEQUIN
    if "earring" in item:
        return _MANNEQUIN_EAR, _TAIL_MANNEQUIN
    if cat in ("bag", "shoes"):
        return _POSE_UPRIGHT, _TAIL_STANDALONE
    return _POSE.get(PRESENT, _POSE["flatlay"]), _TAIL_STANDALONE
_BG = {
    "white": "on a pure seamless white background (RGB 255,255,255)",
    "shadow": "on a soft off-white background with a subtle contact shadow beneath",
}


def find_gguf() -> Path:
    from huggingface_hub import scan_cache_dir
    for repo in scan_cache_dir().repos:
        if repo.repo_id == "city96/FLUX.1-schnell-gguf":
            for rev in repo.revisions:
                for f in rev.files:
                    if f.file_name.endswith(".gguf"):
                        return Path(f.file_path)
    raise SystemExit("FLUX GGUF not in cache - run download_flux.py first")


def _strip_hex(s: str) -> str:
    """Drop hex codes so color stays soft guidance for FLUX (user: 'wiggle
    room'). FLUX doesn't read hex anyway; the plain name is what lands."""
    return re.sub(r"\s*\(?~?#?[0-9a-fA-F]{6}\)?", "", s).replace("()", "").strip()


def build_prompt(g: dict) -> str:
    # the generation-first `prompt` field already uses the plain color name and
    # describes the garment only; fall back to name+desc for old Gemini records
    core = g.get("prompt") or f"{_strip_hex(g.get('color',''))} {g.get('item','')}, {g.get('description','')}"
    core = _strip_hex(core).strip(" ,.")
    pose, tail = pick_pose(g)
    return (
        f"professional e-commerce catalog product photograph of a single item: {core}, "
        f"{pose}, {_BG.get(BG, _BG['white'])}, centered and filling most of the frame, "
        "soft even studio lighting, sharp focus, natural true-to-life color close to the described shade, "
        f"high detail, fabric texture visible, {tail}"
    )


_pipe = None


def get_pipe():
    global _pipe
    if _pipe is None:
        from diffusers import (FluxPipeline, FluxTransformer2DModel,
                               GGUFQuantizationConfig)
        gguf = find_gguf()
        print(f"transformer: {gguf.name}", flush=True)
        transformer = FluxTransformer2DModel.from_single_file(
            str(gguf),
            quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
            config=BASE_REPO, subfolder="transformer", torch_dtype=torch.bfloat16,
        )
        _pipe = FluxPipeline.from_pretrained(
            BASE_REPO, transformer=transformer, torch_dtype=torch.bfloat16)
        _pipe.enable_model_cpu_offload()
        _pipe.vae.enable_slicing()
        print("pipeline ready (model-cpu-offload)", flush=True)
    return _pipe


def shoot(stem: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    garments = json.loads(desc_path(stem).read_text(encoding="utf-8"))
    jobs = [(i, g) for i, g in enumerate(garments) if g.get("category") in SHOT_CATS]
    print(f"{stem}: {len(jobs)} garments", flush=True)
    pipe = get_pipe()
    for idx, g in jobs:
        out = SHOTS / f"{stem}_{idx}_{g.get('category', 'item')}.png"
        if out.exists():
            print(f"  [{idx}] cached", flush=True)
            continue
        t = time.time()
        torch.cuda.reset_peak_memory_stats()
        img = pipe(
            prompt=build_prompt(g),
            num_inference_steps=STEPS, guidance_scale=0.0,
            height=SIZE, width=SIZE,
            generator=torch.Generator("cpu").manual_seed(42),
        ).images[0]
        img.save(out)
        peak = torch.cuda.max_memory_allocated() / 1e9
        print(f"  [{idx}] {g.get('color','')} {g.get('item','')}: "
              f"{time.time()-t:.0f}s, peak {peak:.1f}GB -> {out.name}", flush=True)


def _thumb(path: Path, mx: int = 420) -> str:
    im = Image.open(path); im.load()
    w, h = im.size; sc = min(1.0, mx / max(w, h))
    if sc < 1.0:
        im = im.resize((int(w*sc), int(h*sc)), Image.LANCZOS)
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_review() -> None:
    css = ("body{margin:0;background:#f4f3f2;font-family:Helvetica Neue,Arial,sans-serif;color:#1c1714}"
           "h1{padding:24px 28px 2px;font-size:22px;font-weight:800}.sub{padding:0 28px 16px;color:#8a807b;font-size:13px}"
           ".samp{background:#fff;margin:16px 28px;border-radius:16px;padding:18px;position:relative;"
           "box-shadow:0 14px 34px -24px rgba(80,40,50,.5);display:grid;grid-template-columns:150px 1fr;gap:20px;align-items:start}"
           ".tag{position:absolute;top:-9px;left:20px;background:#cf5c7e;color:#fff;font-size:10px;font-weight:700;padding:2px 10px;border-radius:9px}"
           ".src{width:100%;border-radius:12px}.pairs{display:flex;flex-wrap:wrap;gap:16px}"
           "figure{margin:0;width:150px;text-align:center}"
           "figure img,.fail{width:150px;height:150px;object-fit:contain;border-radius:10px;background:#fafafa;border:1px solid #eee}"
           "figcaption{font-size:10.5px;color:#8a807b;margin-top:5px}.fail{display:flex;align-items:center;justify-content:center;color:#c05}")
    rows, total, ok = [], 0, 0
    for stem in desc_stems():
        shots = sorted(SHOTS.glob(f"{stem}_*.png"))
        if not shots:
            continue
        garments = json.loads(desc_path(stem).read_text(encoding="utf-8"))
        cells = ""
        for idx, g in enumerate(garments):
            if g.get("category") not in SHOT_CATS:
                continue
            total += 1
            label = f"{g.get('color','')} {g.get('item','')}".strip()
            sp = SHOTS / f"{stem}_{idx}_{g.get('category','item')}.png"
            if sp.exists():
                ok += 1
                cells += f'<figure><img src="{_thumb(sp)}"><figcaption>{label}</figcaption></figure>'
            else:
                cells += f'<figure><div class=fail>no shot</div><figcaption>{label}</figcaption></figure>'
        src = SAMPLES / f"{stem}.jpg"
        srcimg = f'<img class=src src="{_thumb(src, 300)}">' if src.exists() else ""
        rows.append(f'<section class=samp><div class=tag>{stem}</div>{srcimg}<div class=pairs>{cells}</div></section>')
    html = (f"<!doctype html><meta charset=utf-8><title>Garment shots - local FLUX</title><style>{css}</style>"
            f"<h1>Garment shots - local FLUX.1 schnell</h1>"
            f"<p class=sub>{ok}/{total} garments. Local Qwen3-VL describe -> FLUX generate. "
            f"Present={PRESENT}, bg={BG}, {STEPS} steps. Zero tokens.</p>" + "".join(rows))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(f"review: {ok}/{total} -> {OUT/'index.html'}", flush=True)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--review-only" in sys.argv:
        build_review(); return
    for stem in (args or ["b2_r1c4"]):
        if not (ANALYSIS / f"{stem}.json").exists():
            print(f"  {stem}: no cached description - run the describe step first", flush=True)
            continue
        shoot(stem)
    build_review()


if __name__ == "__main__":
    main()
