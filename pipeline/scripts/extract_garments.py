"""CPU preview of multi-garment extraction — the Style Me wardrobe auto-fill.

ONE outfit photo -> detect EACH garment (GroundingDINO, zero-shot, on CPU) ->
per-category de-dup -> background-removed cutout per garment (rembg) -> colour
tags -> N wardrobe items + a combined look. Writes:

  review/extract/cutouts/*.png   one transparent cutout per detected garment
  review/extract/looks.json      look-file (garments + one outfit per photo),
                                 the pipeline<->renderer interchange shape
  review/extract/index.html      self-contained visual preview (embeds images)

This is the CPU stand-in so we can SEE extraction on this laptop. The GPU box
runs the same shape with GroundingDINO+SAM2 (crisper masks) + Qwen tags.

Usage (from repo root):
    python pipeline/scripts/extract_garments.py            # 5 random samples
    python pipeline/scripts/extract_garments.py --n 5 --seed 7
    python pipeline/scripts/extract_garments.py samples/sample_r5c2.jpg ...
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import random
import sys
import time
from pathlib import Path

from PIL import Image

PIPELINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PIPELINE.parent))
from pipeline.app.color import color_name, extract_palette  # noqa: E402

SAMPLES = PIPELINE / "samples"
OUTDIR = PIPELINE / "review" / "extract"
CUTOUTS = OUTDIR / "cutouts"

# Open-vocabulary detection labels -> the app's 7 categories. "Everything
# detected" per the locked design: clothes + shoes + bag + accessories.
LABEL_CATEGORY = {
    "shirt": "top", "t-shirt": "top", "blouse": "top", "top": "top",
    "sweater": "top", "knit top": "top", "tank top": "top", "crop top": "top",
    "dress": "dress", "gown": "dress",
    "skirt": "bottom", "pants": "bottom", "trousers": "bottom", "jeans": "bottom",
    "shorts": "bottom", "leggings": "bottom",
    "jacket": "outerwear", "coat": "outerwear", "blazer": "outerwear",
    "cardigan": "outerwear", "trench coat": "outerwear",
    "shoes": "shoes", "sneakers": "shoes", "heels": "shoes", "boots": "shoes",
    "sandals": "shoes",
    "handbag": "bag", "bag": "bag", "backpack": "bag", "tote bag": "bag",
    "hat": "accessory", "scarf": "accessory", "hijab": "accessory",
    "belt": "accessory", "sunglasses": "accessory", "necklace": "accessory",
    "watch": "accessory", "earrings": "accessory",
}
CANDIDATE_LABELS = sorted(LABEL_CATEGORY)
MIN_SCORE = 0.28          # grounding-dino-tiny runs low-confidence; keep it inclusive
NMS_IOU = 0.55            # same-category boxes above this overlap = one garment
MARGIN = 0.05             # crop padding around each detection box
PREVIEW_MAX = 340         # px, longest side for embedded originals
CUT_MAX = 240             # px, longest side for embedded cutouts

_detector = None
_session = None


def get_detector():
    global _detector
    if _detector is None:
        from transformers import pipeline
        print("  loading GroundingDINO (grounding-dino-tiny, CPU)…", flush=True)
        _detector = pipeline(
            "zero-shot-object-detection",
            model="IDEA-Research/grounding-dino-tiny",
            device=-1,
        )
    return _detector


def get_session():
    global _session
    if _session is None:
        from rembg import new_session
        print("  loading rembg background remover (u2net, CPU)…", flush=True)
        _session = new_session("u2net")
    return _session


def _iou(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua else 0.0


def detect(pil: Image.Image) -> list[dict]:
    raw = get_detector()(pil, candidate_labels=CANDIDATE_LABELS)
    dets = []
    for r in raw:
        if r["score"] < MIN_SCORE:
            continue
        cat = LABEL_CATEGORY.get(r["label"].lower())
        if not cat:
            continue
        b = r["box"]
        dets.append({
            "cat": cat, "label": r["label"], "score": float(r["score"]),
            "box": (b["xmin"], b["ymin"], b["xmax"], b["ymax"]),
        })
    return dets


def dedup(dets: list[dict]) -> list[dict]:
    """Per-category NMS: overlapping synonym boxes (shirt/t-shirt/blouse for the
    same top) collapse to the single highest-scoring detection."""
    kept: list[dict] = []
    per_cat: dict[str, list[dict]] = {}
    for d in sorted(dets, key=lambda x: -x["score"]):
        arr = per_cat.setdefault(d["cat"], [])
        if all(_iou(d["box"], k["box"]) < NMS_IOU for k in arr):
            arr.append(d)
            kept.append(d)
    # Stable, human-friendly order: garment top -> bottom, big -> small.
    order = {"outerwear": 0, "dress": 1, "top": 2, "bottom": 3, "shoes": 4, "bag": 5, "accessory": 6}
    kept.sort(key=lambda d: (order.get(d["cat"], 9), -d["score"]))
    return kept


def crop_box(pil: Image.Image, box) -> Image.Image:
    x0, y0, x1, y1 = box
    w, h = pil.size
    mx, my = (x1 - x0) * MARGIN, (y1 - y0) * MARGIN
    return pil.crop((max(0, int(x0 - mx)), max(0, int(y0 - my)),
                     min(w, int(x1 + mx)), min(h, int(y1 + my))))


def cutout(crop: Image.Image) -> Image.Image:
    from rembg import remove
    return remove(crop, session=get_session()).convert("RGBA")


def _thumb(pil: Image.Image, longest: int) -> Image.Image:
    scale = min(1.0, longest / max(pil.size))
    if scale >= 1.0:
        return pil
    return pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))))


def data_uri(pil: Image.Image, fmt="PNG") -> str:
    buf = io.BytesIO()
    pil.save(buf, format=fmt)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def process(img_path: Path) -> dict:
    pil = Image.open(img_path).convert("RGB")
    t0 = time.time()
    dets = dedup(detect(pil))
    garments = []
    CUTOUTS.mkdir(parents=True, exist_ok=True)
    for i, d in enumerate(dets):
        crop = crop_box(pil, d["box"])
        cut = cutout(crop)
        buf = io.BytesIO()
        crop.save(buf, format="JPEG", quality=90)
        colors = extract_palette(buf.getvalue(), count=3)
        name = f"{img_path.stem}__{i}_{d['cat']}.png"
        cut.save(CUTOUTS / name)
        garments.append({
            "id": f"{img_path.stem}-{i}",
            "category": d["cat"],
            "label": d["label"],
            "score": round(d["score"], 2),
            "colors": colors,
            "color_names": [color_name(c) for c in colors],
            "cutout_url": f"cutouts/{name}",
            "cutout_data": data_uri(_thumb(cut, CUT_MAX)),
        })
    dt = time.time() - t0
    print(f"  {img_path.name}: {len(garments)} garments in {dt:.0f}s "
          f"({', '.join(g['category'] for g in garments) or 'none'})", flush=True)
    return {
        "image": img_path.name,
        "orig_data": data_uri(_thumb(pil, PREVIEW_MAX), "JPEG"),
        "seconds": round(dt, 1),
        "garments": garments,
    }


def write_lookfile(results: list[dict]):
    garments, outfits = [], []
    for r in results:
        gids = []
        for g in r["garments"]:
            garments.append({
                "id": g["id"], "category": g["category"],
                "colors": g["colors"], "cutout_url": g["cutout_url"],
            })
            gids.append(g["id"])
        if gids:
            outfits.append({"id": f"look-{Path(r['image']).stem}",
                            "garment_ids": gids, "created_at": 0})
    (OUTDIR / "looks.json").write_text(
        json.dumps({"version": 1, "note": "CPU extraction preview — one outfit photo -> N garments",
                    "garments": garments, "outfits": outfits}, ensure_ascii=False, indent=2),
        encoding="utf-8")


def write_preview(results: list[dict]):
    total = sum(len(r["garments"]) for r in results)
    cards = []
    for r in results:
        chips = "".join(
            f'<div class="g"><img src="{g["cutout_data"]}" alt="">'
            f'<div class="cat">{g["category"]}</div>'
            f'<div class="meta">{g["score"]:.2f} · '
            + "".join(f'<span class="sw" style="background:{c}"></span>' for c in g["colors"])
            + f'</div><div class="cn">{", ".join(g["color_names"][:2])}</div></div>'
            for g in r["garments"]
        ) or '<div class="none">no garments detected</div>'
        cards.append(
            f'<div class="card"><div class="orig"><img src="{r["orig_data"]}" alt="">'
            f'<div class="cap"><b>{r["image"]}</b><br>{len(r["garments"])} garments · {r["seconds"]}s</div></div>'
            f'<div class="arrow">→</div><div class="grid">{chips}</div></div>'
        )
    html = PREVIEW_HTML.replace("__TOTAL__", str(total)).replace("__PHOTOS__", str(len(results))).replace("__CARDS__", "\n".join(cards))
    (OUTDIR / "index.html").write_text(html, encoding="utf-8")


PREVIEW_HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lovänya — Multi-garment extraction preview</title>
<style>
 :root{--pink:#D56F88;--accent:#CE6E86;--head:#48292E;--body:#6E5A5A;--muted:#A2908F;--bg:#E8DADA;--soft:linear-gradient(155deg,#F8E1E1,#F3D2D7)}
 *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--body);font-family:'Poppins',system-ui,Segoe UI,sans-serif}
 .wrap{max-width:1000px;margin:0 auto;padding:24px 16px 80px}
 .eyebrow{font-size:10px;font-weight:600;letter-spacing:1.5px;color:var(--accent);text-transform:uppercase}
 h1{font-family:Georgia,serif;color:var(--head);font-size:26px;margin:2px 0 6px}
 .lede{font-size:13px;max-width:680px}
 .stat{display:inline-block;background:var(--soft);border-radius:12px;padding:8px 14px;margin:10px 8px 0 0;font-size:13px;color:var(--head)}
 .card{background:#fff;border-radius:20px;padding:14px;margin:16px 0;box-shadow:0 16px 34px -22px rgba(206,140,150,.5);
   display:grid;grid-template-columns:190px 26px 1fr;gap:12px;align-items:center}
 @media(max-width:640px){.card{grid-template-columns:1fr;}.arrow{display:none}}
 .orig img{width:100%;border-radius:14px;display:block}
 .cap{font-size:11px;color:var(--muted);margin-top:6px}.cap b{color:var(--head)}
 .arrow{font-size:22px;color:var(--pink);text-align:center}
 .grid{display:flex;flex-wrap:wrap;gap:10px}
 .g{width:110px;background:#faf5f5;border:1px solid #f0dcdc;border-radius:12px;padding:8px;text-align:center}
 .g img{width:100%;height:96px;object-fit:contain;background:
   linear-gradient(45deg,#eee 25%,transparent 25%,transparent 75%,#eee 75%),
   linear-gradient(45deg,#eee 25%,#fff 25%,#fff 75%,#eee 75%);background-size:14px 14px;background-position:0 0,7px 7px;border-radius:8px}
 .cat{font-size:12px;font-weight:600;color:var(--head);text-transform:capitalize;margin-top:5px}
 .meta{font-size:10px;color:var(--muted);margin-top:2px}
 .sw{display:inline-block;width:9px;height:9px;border-radius:50%;margin-left:2px;vertical-align:middle;border:1px solid rgba(0,0,0,.1)}
 .cn{font-size:10px;color:var(--body);text-transform:capitalize}
 .none{font-size:12px;color:var(--muted);font-style:italic}
</style></head><body><div class="wrap">
 <div class="eyebrow">Lovänya · Style Me auto-fill</div>
 <h1>One photo → many garments</h1>
 <p class="lede">CPU preview of multi-garment extraction: each outfit photo is detected garment-by-garment
   (GroundingDINO) and each piece is cut out (background removed) into its own wardrobe item. On the GPU box,
   SAM2 gives crisper masks and Qwen adds richer tags — same shape, better pixels.</p>
 <div><span class="stat"><b>__PHOTOS__</b> photos</span><span class="stat"><b>__TOTAL__</b> garments extracted</span>
   <span class="stat">checkerboard = transparent background</span></div>
 __CARDS__
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("images", nargs="*", help="specific sample paths; default = random")
    ap.add_argument("--n", type=int, default=5, help="how many random samples (default 5)")
    ap.add_argument("--seed", type=int, default=42, help="random seed for the pick")
    args = ap.parse_args()

    if args.images:
        paths = [Path(p) for p in args.images]
    else:
        pool = sorted(SAMPLES.glob("*.jpg"))
        random.seed(args.seed)
        paths = random.sample(pool, min(args.n, len(pool)))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    print(f"Extracting garments from {len(paths)} photos: {', '.join(p.name for p in paths)}")

    results = [process(p) for p in paths]
    write_lookfile(results)
    write_preview(results)
    total = sum(len(r["garments"]) for r in results)
    print(f"\n{total} garments from {len(paths)} photos")
    print(f"  preview : {OUTDIR / 'index.html'}")
    print(f"  lookfile: {OUTDIR / 'looks.json'}")
    print(f"  cutouts : {CUTOUTS}/")


if __name__ == "__main__":
    main()
