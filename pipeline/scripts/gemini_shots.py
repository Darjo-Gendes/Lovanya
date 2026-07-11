"""Nano Banana garment pipeline: worn photo -> garment manifest -> catalog shots.

Replaces the DINO->SAM2->SDXL chain (see config.PRODUCT_BACKEND). One Gemini
vision call lists every garment; one Nano Banana call per garment reconstructs
it as a Uniqlo-style flat-lay product shot. Resumable: existing analysis JSONs
and shot PNGs are skipped, manifest + review page are rebuilt fresh from disk
each run (never trust a stale manifest — that bug bit us once).

Usage:
  python pipeline/scripts/gemini_shots.py                # previous batch stems
  python pipeline/scripts/gemini_shots.py b2_r1c4 ...    # explicit stems
  python pipeline/scripts/gemini_shots.py --review-only  # just rebuild HTML
"""
from __future__ import annotations

import base64
import io
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]          # pipeline/
SAMPLES = ROOT / "samples"
OLD_SHOTS = ROOT / "review" / "garments" / "shots"  # previous local-pipeline output
OUT = ROOT / "review" / "garments_gemini"
ANALYSIS = OUT / "analysis"
SHOTS = OUT / "shots"

API = "https://generativelanguage.googleapis.com/v1beta/models"
# Preference order; runtime demotes models the key's tier rejects (e.g. the
# free tier has 0 RPD on 3.1-flash-image and silently works on 2.5-flash-image).
ANALYSIS_PREF = ["gemini-3.5-flash", "gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]
IMAGE_PREF = ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
# Everything detected gets a shot — the wardrobe wants accessories and shoes
# too (user call, 2026-07-10: "there is clearly a watch, add that into the
# wardrobe"). Trim via env if a run needs to save quota.
SHOT_CATS = set(os.environ.get(
    "LOVANYA_SHOT_CATS", "hijab,top,bottom,dress,outerwear,bag,shoes,accessory").split(","))
SLEEP = float(os.environ.get("LOVANYA_GEMINI_SLEEP", "2"))
WORKERS = int(os.environ.get("LOVANYA_GEMINI_WORKERS", "2"))

_lock = threading.Lock()
_stats = {"calls": 0, "images": 0, "by_model": {}, "tok_in": 0, "tok_out": 0}


def _log_usage(kind: str, stem: str, i: int | None, model: str, resp: dict) -> str:
    """Record real token consumption (usageMetadata) per call to usage.jsonl."""
    u = resp.get("usageMetadata", {})
    tin = u.get("promptTokenCount", 0)
    tout = u.get("candidatesTokenCount", 0)
    with _lock:
        _stats["tok_in"] += tin
        _stats["tok_out"] += tout
        with open(OUT / "usage.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind,
                                "stem": stem, "i": i, "model": model,
                                "tokens_in": tin, "tokens_out": tout}) + "\n")
    return f"{tin}in+{tout}out tok"


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        env = ROOT.parent / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("GEMINI_API_KEY not set (env var or .env at repo root)")
    return key


KEY = _api_key()


class QuotaExhausted(Exception):
    pass


def _call(model: str, payload: dict, tries: int = 4) -> dict:
    body = json.dumps(payload).encode()
    for attempt in range(tries):
        req = urllib.request.Request(
            f"{API}/{model}:generateContent",
            data=body,
            headers={"x-goog-api-key": KEY, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                out = json.load(r)
            with _lock:
                _stats["calls"] += 1
                _stats["by_model"][model] = _stats["by_model"].get(model, 0) + 1
            return out
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:800]
            if e.code == 429:
                delay = 15.0
                m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', detail)
                if m:
                    delay = float(m.group(1)) + 1
                if attempt == tries - 1:
                    raise QuotaExhausted(f"{model}: 429 persisted ({detail[:200]})")
                print(f"    429 on {model}, waiting {delay:.0f}s", flush=True)
                time.sleep(delay)
            elif e.code in (403, 404):
                raise QuotaExhausted(f"{model}: HTTP {e.code} ({detail[:200]})")
            elif e.code >= 500 and attempt < tries - 1:
                time.sleep(10 * (attempt + 1))
            else:
                raise RuntimeError(f"{model}: HTTP {e.code} ({detail[:300]})")
    raise RuntimeError(f"{model}: retries exhausted")


class ModelPicker:
    """Walk a preference list, demoting models the key's tier rejects."""

    def __init__(self, pref: list[str], pinned: str):
        self.models = [pinned] if pinned and pinned != "auto" else list(pref)
        self.idx = 0

    def call(self, payload: dict) -> tuple[dict, str]:
        while self.idx < len(self.models):
            model = self.models[self.idx]
            try:
                return _call(model, payload), model
            except QuotaExhausted as e:
                with _lock:
                    if self.idx < len(self.models) - 1:
                        print(f"  !! {e} -> falling back to {self.models[self.idx + 1]}", flush=True)
                        self.idx += 1
                    else:
                        raise
        raise QuotaExhausted("all models exhausted")


ANALYZER = ModelPicker(ANALYSIS_PREF, os.environ.get("LOVANYA_GEMINI_ANALYSIS_MODEL", "auto"))
SHOOTER = ModelPicker(IMAGE_PREF, os.environ.get("LOVANYA_GEMINI_IMAGE_MODEL", "auto"))

ANALYSIS_PROMPT = """You are cataloging garments for a modest-fashion (hijab) styling service.
List EVERY distinct clothing item and accessory the person in this photo is wearing or carrying.
Be exhaustive:
- A hijab/headscarf is usually present in these photos - check for it.
- List EACH visible layer separately (e.g. a shirt/kemeja worn under a sweater, a blazer over a top).
- Include outerwear, tops, bottoms, dresses/abayas, bags, shoes, belts, visible accessories.
- Do NOT include background objects, furniture, bedding, pillows, or anything not worn/carried.
- Colors must be precise (distinguish navy vs blue vs grey; if two layers differ, say which is which).
Return a JSON array; each element: {"item": "short name", "category": "hijab|top|bottom|dress|outerwear|bag|shoes|accessory", "color": "precise color", "description": "one line: fabric, cut, notable details"}.
JSON only."""


def _img_part(path: Path, max_px: int = 1024) -> dict:
    im = Image.open(path)
    im.load()
    w, h = im.size
    sc = min(1.0, max_px / max(w, h))
    if sc < 1.0:
        im = im.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=88)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}


def analyze(stem: str) -> list[dict]:
    out_file = ANALYSIS / f"{stem}.json"
    if out_file.exists():
        return json.loads(out_file.read_text(encoding="utf-8"))
    payload = {
        "contents": [{"parts": [_img_part(SAMPLES / f"{stem}.jpg"), {"text": ANALYSIS_PROMPT}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    resp, model = ANALYZER.call(payload)
    usage = _log_usage("analysis", stem, None, model, resp)
    text = "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    garments = json.loads(text)
    if not isinstance(garments, list):
        raise ValueError(f"{stem}: analysis returned non-list")
    out_file.write_text(json.dumps(garments, indent=2), encoding="utf-8")
    print(f"  {stem}: {len(garments)} items via {model} ({usage}): "
          + ", ".join(f"{g.get('color','')} {g.get('item','')}".strip() for g in garments), flush=True)
    return garments


def _shot_prompt(g: dict, soft: bool = False) -> str:
    name = f"{g.get('color', '')} {g.get('item', '')}".strip()
    desc = g.get("description", "")
    pose = ("displayed upright in standard product-photo orientation"
            if g.get("category") in ("bag", "shoes")
            else "laid perfectly flat, photographed straight from directly above (top-down flat-lay)")
    if soft:
        return (f"Product photograph of a {name} ({desc}), matching the garment shown in the "
                f"reference photo: {pose}, neatly arranged, centered on a pure white seamless "
                f"background, soft even studio lighting, e-commerce catalog style, garment only.")
    return (f"Create a professional e-commerce catalog product photo of ONLY this item from the "
            f"photo: the {name} - {desc}. Style: exactly like a Uniqlo online-store product image "
            f"- the garment alone, {pose}, neatly arranged and smoothed, centered and filling most "
            f"of the frame, on a pure white seamless background (RGB 255,255,255), soft even "
            f"studio lighting. Faithfully preserve the real garment's exact color, fabric texture, "
            f"seams, stitching and proportions as seen in the photo. The image must contain NO "
            f"person, NO body parts, NO face, NO mannequin, NO other clothing items, NO props, "
            f"NO text or watermarks.")


def _extract_image(resp: dict) -> bytes | None:
    for cand in resp.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            data = part.get("inlineData", part.get("inline_data", {}))
            if data.get("data"):
                return base64.b64decode(data["data"])
    return None


def shoot(stem: str, idx: int, g: dict) -> dict:
    cat = g.get("category", "item")
    out_file = SHOTS / f"{stem}_{idx}_{cat}.png"
    rec = {"sample": f"{stem}.jpg", "stem": stem, "i": idx, **{k: g.get(k, "") for k in
           ("item", "category", "color", "description")}, "shot": None, "model": None}
    if out_file.exists():
        rec["shot"] = out_file.name
        rec["model"] = "cached"
        return rec
    src = _img_part(SAMPLES / f"{stem}.jpg")
    for soft in (False, True):
        payload = {
            "contents": [{"parts": [src, {"text": _shot_prompt(g, soft=soft)}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        try:
            resp, model = SHOOTER.call(payload)
        except (QuotaExhausted, RuntimeError) as e:
            print(f"  {stem}[{idx}] {cat}: FAILED {e}", flush=True)
            return rec
        usage = _log_usage("shot", stem, idx, model, resp)
        img = _extract_image(resp)
        if img:
            out_file.write_bytes(img)
            rec["shot"] = out_file.name
            rec["model"] = model
            with _lock:
                _stats["images"] += 1
            print(f"  {stem}[{idx}] {g.get('color','')} {g.get('item','')}: OK via {model} ({usage})"
                  + (" (soft retry)" if soft else ""), flush=True)
            time.sleep(SLEEP)
            return rec
        reason = (resp.get("candidates") or [{}])[0].get("finishReason", "no image")
        print(f"  {stem}[{idx}] {cat}: no image ({reason})" + ("" if soft else ", soft retry"), flush=True)
        time.sleep(SLEEP)
    return rec


def _thumb_uri(path: Path, max_px: int = 420) -> str:
    im = Image.open(path)
    im.load()
    w, h = im.size
    sc = min(1.0, max_px / max(w, h))
    if sc < 1.0:
        im = im.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
    buf = io.BytesIO()
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im.convert("RGBA").save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True)
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"


CSS = """body{margin:0;background:#f4f3f2;font-family:Helvetica Neue,Arial,sans-serif;color:#1c1714}
h1{padding:24px 28px 2px;font-size:22px;font-weight:800}.sub{padding:0 28px 16px;color:#8a807b;font-size:13px}
.samp{background:#fff;margin:16px 28px;border-radius:16px;padding:18px;position:relative;
box-shadow:0 14px 34px -24px rgba(80,40,50,.5);display:grid;grid-template-columns:150px 1fr;gap:20px;align-items:start}
.tag{position:absolute;top:-9px;left:20px;background:#cf5c7e;color:#fff;font-size:10px;font-weight:700;padding:2px 10px;border-radius:9px}
.src{width:100%;border-radius:12px}.pairs{display:flex;flex-wrap:wrap;gap:18px}
figure{margin:0;width:150px;text-align:center}
figure img,.fail{width:150px;height:188px;object-fit:contain;border-radius:10px;background:#fafafa;border:1px solid #eee}
figcaption{font-size:10.5px;color:#8a807b;margin-top:5px}
.fail{display:flex;align-items:center;justify-content:center;color:#c05;font-size:11px}
.old{grid-column:1/-1;border-top:1px dashed #e8e2df;padding-top:10px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.old img{width:72px;height:90px;object-fit:contain;border-radius:8px;border:1px solid #eee}
.oldlbl{font-size:10px;color:#b9b0ab;width:84px}"""


def build_review() -> None:
    rows, manifest, total, ok = [], [], 0, 0
    stems = sorted(p.stem for p in ANALYSIS.glob("*.json"))
    for stem in stems:
        garments = json.loads((ANALYSIS / f"{stem}.json").read_text(encoding="utf-8"))
        cells = ""
        for i, g in enumerate(garments):
            if g.get("category") not in SHOT_CATS:
                continue
            total += 1
            label = f"{g.get('color','')} {g.get('item','')}".strip()
            shot = SHOTS / f"{stem}_{i}_{g.get('category','item')}.png"
            rec = {"sample": f"{stem}.jpg", "i": i, **{k: g.get(k, "") for k in
                   ("item", "category", "color", "description")},
                   "shot": shot.name if shot.exists() else None}
            manifest.append(rec)
            if shot.exists():
                ok += 1
                cells += f'<figure><img src="{_thumb_uri(shot)}"><figcaption>{label}</figcaption></figure>'
            else:
                cells += f'<figure><div class=fail>no shot</div><figcaption>{label}</figcaption></figure>'
        old_html = ""
        for label, folder in (("old local pipeline", OLD_SHOTS),
                              ("local qwen (lightning 8-step)", OUT / "local_qwen_lightning"),
                              ("local qwen (standard cfg4)", OUT / "local_qwen")):
            found = sorted(folder.glob(f"{stem}_*.png")) if folder.exists() else []
            if found:
                imgs = "".join(f'<img src="{_thumb_uri(p, 180)}">' for p in found)
                old_html += f'<div class=old><span class=oldlbl>{label}</span>{imgs}</div>'
        rows.append(
            f'<section class=samp><div class=tag>{stem}</div>'
            f'<img class=src src="{_thumb_uri(SAMPLES / (stem + ".jpg"))}">'
            f'<div class=pairs>{cells}</div>{old_html}</section>')
    (OUT / "manifest.jsonl").write_text(
        "\n".join(json.dumps(m) for m in manifest) + "\n", encoding="utf-8")
    html = (f'<!doctype html><meta charset=utf-8><title>Garment shots - Nano Banana</title>'
            f'<style>{CSS}</style><h1>Garment shots - Nano Banana</h1>'
            f'<p class=sub>{ok}/{total} garments from {len(stems)} outfits. '
            f'Gemini analysis + single-call product-shot reconstruction. '
            f'Dashed strip below each outfit = previous local pipeline for comparison.</p>'
            + "".join(rows))
    (OUT / "index.html").write_text(html, encoding="utf-8")
    print(f"review: {ok}/{total} shots, {len(stems)} outfits, "
          f"{len(html) / 1e6:.2f} MB -> {OUT / 'index.html'}", flush=True)


def previous_batch_stems(target: int = 20) -> list[str]:
    """Same outfits as the previous iteration (its cutouts dir), topped up to 20."""
    prev = ROOT / "review" / "garments" / "cutouts"
    stems = sorted({re.sub(r"_\d+_[a-z]+$", "", p.stem) for p in prev.glob("*.png")})
    have = set(stems)
    pool = sorted(p.stem for p in SAMPLES.glob("*.jpg") if p.stem not in have)
    rng = random.Random(42)
    while len(stems) < target and pool:
        stems.append(pool.pop(rng.randrange(len(pool))))
    return stems[:target]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for d in (ANALYSIS, SHOTS):
        d.mkdir(parents=True, exist_ok=True)
    if "--review-only" in sys.argv:
        build_review()
        return
    stems = args or previous_batch_stems()
    print(f"batch: {len(stems)} outfits -> {OUT}", flush=True)

    jobs = []
    for stem in stems:
        if not (SAMPLES / f"{stem}.jpg").exists():
            print(f"  {stem}: sample missing, skipped", flush=True)
            continue
        try:
            garments = analyze(stem)
        except Exception as e:
            print(f"  {stem}: analysis FAILED {e}", flush=True)
            continue
        if "--no-shots" not in sys.argv:
            jobs += [(stem, i, g) for i, g in enumerate(garments) if g.get("category") in SHOT_CATS]
        time.sleep(1)

    print(f"shots: {len(jobs)} garments queued, {WORKERS} workers", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(lambda j: shoot(*j), jobs))

    build_review()
    print(f"done: {_stats['calls']} API calls, {_stats['images']} new images, "
          f"per model {_stats['by_model']}", flush=True)
    print(f"tokens: {_stats['tok_in']} in + {_stats['tok_out']} out "
          f"(~${_stats['tok_out'] / 1290 * 0.039:.2f} of image output at 2.5-flash-image "
          f"list price; full log in {OUT / 'usage.jsonl'})", flush=True)


if __name__ == "__main__":
    main()
