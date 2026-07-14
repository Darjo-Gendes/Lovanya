"""OminiControl production pipeline — image-conditioned product shots, batch.

The winning stack (comparison card 5) with the bag-bundle fixes folded in for
EVERY garment:
  - conditions: SAM2 mask -> largest connected component (drops contamination)
    -> gray-world white-balanced pixels -> white 512^2 + unsharp;
  - measured color: masked-median shade (deterministic) injected for
    solid-pattern items — VLM color judgment stays for prints;
  - prompts: v2.2 archetype descriptions (taxonomy carries canonical
    completion for bags) + per-category presentation (hijab/necklace/earrings
    on featureless mannequin forms, bags/shoes standalone upright);
  - condition_scale 1.3 for rigid goods (bag/shoes/accessory), 1.0 for cloth;
  - resume: existing shots are skipped, so reruns are cheap and crash-safe.

Phases per run: build ALL conditions (SAM2), free it, load the mmgp pipe once
(profile 5 + int8), generate everything, build the self-contained review.

Usage:
  python pipeline/scripts/omini_gp_shots.py --batch          # previous-20 set
  python pipeline/scripts/omini_gp_shots.py b2_r1c4 [...]    # explicit stems
  python pipeline/scripts/omini_gp_shots.py --review-only
"""
from __future__ import annotations

import gc
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import numpy as np
import torch
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))                    # pipeline/ (config)
sys.path.insert(0, str(ROOT.parent))             # repo root (pipeline.app.*)
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor" / "OminiControlGP"))

OUT = ROOT / "review" / "garments_omini"
CONDS = OUT / "conditions"
SHOTS = OUT / "shots"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
SAMPLES = ROOT / "samples"
BASE_REPO = "YuCollection/FLUX.1-schnell-Diffusers"

CATEGORIES = ("hijab", "top", "bottom", "dress", "outerwear", "bag", "shoes", "accessory")
RIGID = ("bag", "shoes", "accessory")
SEED = int(os.environ.get("LOVANYA_SEED", "42"))

SHADES = {
    "black": (20, 18, 16), "dark chocolate brown": (60, 42, 30),
    "dark brown": (78, 53, 36), "chestnut brown": (110, 74, 48),
    "tan": (176, 138, 98), "beige": (206, 184, 154),
    "warm sand beige": (210, 180, 140), "dark olive green": (72, 70, 42),
    "navy blue": (28, 34, 62), "burgundy": (88, 32, 40),
    "grey": (128, 126, 122), "light grey": (180, 178, 174),
    "cream": (238, 230, 210), "white": (248, 246, 242),
    "soft taupe": (168, 152, 138), "dusty pink": (200, 160, 156),
    "light blue": (160, 185, 210),
}

_POSE_MANNEQUIN_HEAD = ("styled as worn on a smooth featureless abstract white display "
                        "mannequin head with no facial features, neat elegant drape, front view")
_POSE_MANNEQUIN_BUST = ("displayed on a minimalist featureless white mannequin bust form, "
                        "neck and shoulders only with no face")
_POSE_MANNEQUIN_EAR = ("displayed on the ear of a smooth featureless white mannequin head "
                       "with no facial features, close-up view")
_POSE_UPRIGHT = ("shown entirely by itself resting upright on a plain surface, completely "
                 "unworn, not on any body or mannequin")
_POSE_FLAT = "shown alone, laid out neatly"

_TAIL_STANDALONE = "No person, no body, no face, no mannequin, no props, no text."
_TAIL_MANNEQUIN = ("Only the item and its plain featureless display form - no human skin, "
                   "no facial features, no hair, no other clothing, no props, no text.")


def pick_pose(g: dict) -> tuple[str, str]:
    cat = g.get("category", "")
    item = f"{g.get('item','')} {g.get('archetype','')}".lower()
    if cat == "hijab":
        return _POSE_MANNEQUIN_HEAD, _TAIL_MANNEQUIN
    if "necklace" in item or "pendant" in item:
        return _POSE_MANNEQUIN_BUST, _TAIL_MANNEQUIN
    if "earring" in item:
        return _POSE_MANNEQUIN_EAR, _TAIL_MANNEQUIN
    if cat in ("bag", "shoes"):
        return _POSE_UPRIGHT, _TAIL_STANDALONE
    return _POSE_FLAT, _TAIL_STANDALONE


def _strip_hex(s: str) -> str:
    return re.sub(r"\s*\(?~?#?[0-9a-fA-F]{6}\)?", "", str(s)).replace("()", "").strip()


def gray_world_wb(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    means = a.reshape(-1, 3).mean(axis=0)
    a = np.clip(a * (means.mean() / np.maximum(means, 1e-4)), 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def nearest_shade(rgb) -> str:
    r, g, b = rgb
    return min(SHADES, key=lambda k: (SHADES[k][0]-r)**2 + (SHADES[k][1]-g)**2 + (SHADES[k][2]-b)**2)


def largest_component(mask: np.ndarray) -> np.ndarray:
    import cv2
    n, labels = cv2.connectedComponents(mask.astype(np.uint8))
    if n <= 2:
        return mask
    sizes = [(labels == i).sum() for i in range(1, n)]
    return labels == (1 + int(np.argmax(sizes)))


def rescale_bbox(bbox, w: int, h: int, cat: str):
    x1, y1, x2, y2 = [float(v) for v in bbox]
    if max(x1, y1, x2, y2) > max(w, h) + 2:          # 0-1000 normalized
        x1, x2 = x1 * w / 1000, x2 * w / 1000
        y1, y2 = y1 * h / 1000, y2 * h / 1000
    if cat == "bag":                                  # body hangs below strap box
        bh, bw = y2 - y1, x2 - x1
        y2 = min(h, y2 + 0.9 * bh)
        x1, x2 = max(0, x1 - 0.35 * bw), min(w, x2 + 0.35 * bw)
    return x1, y1, x2, y2


def build_condition(wb: Image.Image, bbox, cat: str, out_file: Path):
    """WB image + box -> cleaned 512^2 condition on white + measured shade.
    Returns (ok, shade)."""
    from pipeline.app.cutout import sam2_mask
    w, h = wb.size
    try:
        box = rescale_bbox(bbox, w, h, cat)
    except (TypeError, ValueError):
        return False, ""
    if box[2] - box[0] < 4 or box[3] - box[1] < 4:
        return False, ""
    mask = sam2_mask(wb, box)
    mask = largest_component(mask)
    ys, xs = np.where(mask)
    if len(xs) < 30:
        return False, ""
    shade = nearest_shade(tuple(np.median(np.asarray(wb)[ys, xs], axis=0)))
    rgba = wb.convert("RGBA")
    alpha = Image.fromarray((mask * 255).astype(np.uint8), "L").resize(rgba.size)
    rgba.putalpha(alpha)
    cut = rgba.crop((xs.min(), ys.min(), max(xs.min()+1, xs.max()), max(ys.min()+1, ys.max())))
    side = max(cut.size)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    sq.paste(cut, ((side - cut.width) // 2, (side - cut.height) // 2), cut)
    cond = sq.convert("RGB").resize((512, 512), Image.LANCZOS)
    cond = cond.filter(ImageFilter.UnsharpMask(radius=3, percent=120, threshold=2))
    cond.save(out_file)
    return True, shade


def build_prompt(g: dict, shade: str) -> str:
    core = _strip_hex(g.get("prompt") or f"{g.get('color','')} {g.get('item','')}").strip(" ,.")
    pattern = str(g.get("attributes", {}).get("pattern", "solid")).lower()
    color_line = ""
    if shade and ("solid" in pattern or "plain" in pattern or not pattern.strip()):
        color_line = f" The item's exact color is {shade}."
    pose, tail = pick_pose(g)
    return (f"professional e-commerce catalog product photograph of this exact item: {core}."
            f"{color_line} The item is {pose}, centered on a pure seamless white background, "
            f"soft even studio lighting, sharp focus, true to the reference item's real color, "
            f"shape, proportions and material. {tail}")


def stems_for_batch() -> list[str]:
    from gemini_shots import previous_batch_stems
    return previous_batch_stems(20)


def _color_flagged_ids() -> set[str]:
    """Shot ids the confidence pass marked as a render-vs-spec color mismatch."""
    p = OUT / "confidence.json"
    if not p.exists():
        return set()
    conf = json.loads(p.read_text(encoding="utf-8"))
    return {sid for sid, c in conf.items()
            if c.get("color") and c["color"].get("mismatch")}


def collect_jobs(stems: list[str]) -> list[dict]:
    """Build/refresh conditions for every garment with a valid description.
    Color-flagged items get their condition recolored toward the intended hue
    (the auto-fix for the black->olive class of render bug)."""
    from confidence import recolor_condition
    from PIL import Image as _Image
    flagged = _color_flagged_ids()
    CONDS.mkdir(parents=True, exist_ok=True)
    jobs = []
    for stem in stems:
        desc = DESCS / f"{stem}.json"
        src = SAMPLES / f"{stem}.jpg"
        if not desc.exists() or not src.exists():
            print(f"  {stem}: missing description or sample, skipped", flush=True)
            continue
        garments = json.loads(desc.read_text(encoding="utf-8"))
        wb = gray_world_wb(Image.open(src).convert("RGB"))
        for i, g in enumerate(garments):
            if g.get("category") not in CATEGORIES or g.get("_parse_error"):
                continue
            shot = SHOTS / f"{stem}_{i}_{g.get('category')}.png"
            if shot.exists():
                jobs.append({"stem": stem, "i": i, "g": g, "shot": shot, "cached": True})
                continue
            cond_file = CONDS / f"{stem}_{i}_{g.get('category')}.png"
            ok, shade = build_condition(wb, g.get("bbox"), g.get("category"), cond_file)
            if not ok:
                print(f"  {stem}[{i}] {g.get('item')}: condition failed, skipped", flush=True)
                continue
            shot_id = f"{stem}_{i}_{g.get('category')}"
            job = {"stem": stem, "i": i, "g": g, "shot": shot, "cond": cond_file,
                   "shade": shade, "cached": False}
            if shot_id in flagged:  # color-flagged -> recolor the OUTPUT after gen
                job["recolor_hex"] = g.get("color", "")
                print(f"  {stem}[{i}] {g.get('item')}: will recolor output -> '{g.get('color')}'", flush=True)
            jobs.append(job)
    return jobs


def load_pipe():
    from diffusers.pipelines import FluxPipeline
    t0 = time.time()
    pipe = FluxPipeline.from_pretrained(BASE_REPO, torch_dtype=torch.bfloat16)
    pipe.load_lora_weights("Yuanshi/OminiControl",
                           weight_name="omini/subject_512.safetensors",
                           adapter_name="subject")
    from mmgp import offload  # AFTER load: its safetensors patch breaks transformers 5
    offload.profile(pipe, profile_no=5, verboseLevel=1, quantizeTransformer=True)
    print(f"pipe ready in {time.time()-t0:.0f}s", flush=True)
    return pipe


def _thumb(path: Path, mx: int = 420) -> str:
    import base64
    import io
    im = Image.open(path); im.load()
    w, h = im.size
    sc = min(1.0, mx / max(w, h))
    if sc < 1.0:
        im = im.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_review() -> None:
    css = ("body{margin:0;background:#f4f3f2;font-family:Helvetica Neue,Arial,sans-serif;color:#1c1714}"
           "h1{padding:24px 28px 2px;font-size:22px;font-weight:800}.sub{padding:0 28px 16px;color:#8a807b;font-size:13px}"
           ".samp{background:#fff;margin:16px 28px;border-radius:16px;padding:18px;position:relative;"
           "box-shadow:0 14px 34px -24px rgba(80,40,50,.5);display:grid;grid-template-columns:150px 1fr;gap:20px;align-items:start}"
           ".tag{position:absolute;top:-9px;left:20px;background:#cf5c7e;color:#fff;font-size:10px;font-weight:700;padding:2px 10px;border-radius:9px}"
           ".src{width:100%;border-radius:12px}.pairs{display:flex;flex-wrap:wrap;gap:16px}"
           "figure{margin:0;width:150px;text-align:center}"
           "figure img{width:150px;height:150px;object-fit:contain;border-radius:10px;background:#fafafa;border:1px solid #eee}"
           "figcaption{font-size:10.5px;color:#8a807b;margin-top:5px}")
    rows, total = [], 0
    stems = sorted({p.name.rsplit("_", 2)[0] for p in SHOTS.glob("*.png")})
    for stem in stems:
        desc = DESCS / f"{stem}.json"
        garments = json.loads(desc.read_text(encoding="utf-8")) if desc.exists() else []
        cells = ""
        for p in sorted(SHOTS.glob(f"{stem}_*.png"),
                        key=lambda q: int(q.stem.rsplit("_", 2)[1])):
            i = int(p.stem.rsplit("_", 2)[1])
            g = garments[i] if i < len(garments) else {}
            label = _strip_hex(f"{g.get('color','')} {g.get('archetype', g.get('item',''))}").strip()
            cells += f'<figure><img src="{_thumb(p)}"><figcaption>{label}</figcaption></figure>'
            total += 1
        src = SAMPLES / f"{stem}.jpg"
        srcimg = f'<img class=src src="{_thumb(src, 300)}">' if src.exists() else ""
        rows.append(f'<section class=samp><div class=tag>{stem}</div>{srcimg}'
                    f'<div class=pairs>{cells}</div></section>')
    html = (f"<!doctype html><meta charset=utf-8><title>Lovanya wardrobe - OminiControl batch</title>"
            f"<style>{css}</style><h1>Wardrobe product shots - image-conditioned local pipeline</h1>"
            f"<p class=sub>{total} garments from {len(stems)} outfits. Qwen3-VL two-pass describe "
            f"-> SAM2 white-balanced cutout -> OminiControl subject-conditioned FLUX schnell. "
            f"Local, ~25s/garment, $0.</p>" + "".join(rows))
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(f"review: {total} shots, {len(stems)} outfits -> {OUT/'index.html'}", flush=True)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--review-only" in sys.argv:
        build_review()
        return
    stems = args if args else (stems_for_batch() if "--batch" in sys.argv else ["b2_r1c4"])
    print(f"batch: {len(stems)} outfits", flush=True)

    jobs = collect_jobs(stems)
    todo = [j for j in jobs if not j["cached"]]
    print(f"jobs: {len(jobs)} garments total, {len(todo)} to generate "
          f"({len(jobs)-len(todo)} cached)", flush=True)
    if not todo:
        build_review()
        return

    # free SAM2 before the generator takes the card
    import pipeline.app.cutout as cutout_mod
    cutout_mod._model = None
    cutout_mod._processor = None
    gc.collect()
    torch.cuda.empty_cache()

    from src.flux.condition import Condition
    from src.flux.generate import generate, seed_everything
    pipe = load_pipe()
    SHOTS.mkdir(parents=True, exist_ok=True)

    done = errors = 0
    for j in todo:
        g = j["g"]
        try:
            cond_img = Image.open(j["cond"]).convert("RGB").resize((512, 512))
            condition = Condition("subject", cond_img, position_delta=(0, 32))
            scale = 1.3 if g.get("category") in RIGID else 1.0
            t = time.time()
            seed_everything(SEED)
            img = generate(pipe, prompt=build_prompt(g, j.get("shade", "")),
                           conditions=[condition], condition_scale=scale,
                           num_inference_steps=8, height=512, width=512).images[0]
            # color auto-fix: OminiControl's color conditioning is too weak to
            # force a spec color onto FLUX's shape-prior, so correct the OUTPUT
            # deterministically (retoucher-style) when the item was color-flagged.
            if j.get("recolor_hex"):
                from confidence import recolor_condition
                img = recolor_condition(img.convert("RGB"), j["recolor_hex"])
            img.save(j["shot"])
            done += 1
            print(f"  [{done}/{len(todo)}] {j['stem']}[{j['i']}] "
                  f"{g.get('item','?')}: {time.time()-t:.0f}s", flush=True)
        except Exception as e:  # keep the batch alive; report at the end
            errors += 1
            print(f"  ERROR {j['stem']}[{j['i']}] {g.get('item','?')}: {e}", flush=True)

    build_review()
    print(f"BATCH DONE: {done} generated, {errors} errors", flush=True)


if __name__ == "__main__":
    main()
