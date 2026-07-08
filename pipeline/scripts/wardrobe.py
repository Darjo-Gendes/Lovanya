"""One outfit photo -> a Shein/Uniqlo-style digital wardrobe.

detect each garment (GroundingDINO) -> SAM2 clean cutout -> lay them out as
e-commerce product cards (cutout on white, name, category, dominant color).
All local, on-GPU, zero tokens.

Run from the repo root:
    python pipeline/scripts/wardrobe.py path/to/outfit.jpg
"""
import base64
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

import extract_garments as eg  # noqa: E402
from pipeline.app.cutout import sam2_cutout  # noqa: E402

PIPELINE = Path(__file__).resolve().parent.parent
OUTDIR = PIPELINE / "review" / "wardrobe"

# nicer product names per detected category/label
NAME = {
    "outerwear": "Overshirt / Layer", "top": "Top", "bottom": "Bottoms",
    "dress": "Dress", "shoes": "Footwear", "bag": "Bag", "accessory": "Accessory",
}
BASIC_COLORS = {
    "black": (20, 20, 20), "white": (240, 240, 240), "grey": (128, 128, 128),
    "navy": (30, 40, 80), "blue": (60, 110, 200), "red": (200, 50, 50),
    "pink": (235, 130, 170), "green": (70, 140, 80), "beige": (215, 195, 165),
    "brown": (120, 85, 60), "cream": (240, 230, 205), "yellow": (225, 205, 90),
    "purple": (130, 80, 160), "orange": (230, 140, 60),
}


def dominant_color(rgba: Image.Image):
    """Average of the opaque pixels -> nearest basic color name + hex."""
    import numpy as np
    a = np.asarray(rgba.convert("RGBA"))
    mask = a[..., 3] > 40
    if mask.sum() == 0:
        return "neutral", "#cccccc"
    px = a[mask][:, :3].mean(axis=0)
    r, g, b = px
    # bright + low-saturation reads as white/cream before nearest-color match
    if min(r, g, b) > 195 and (max(r, g, b) - min(r, g, b)) < 25:
        return ("white" if min(r, g, b) > 220 else "cream"), "#%02x%02x%02x" % (int(r), int(g), int(b))
    name = min(BASIC_COLORS, key=lambda k: sum((px[i] - BASIC_COLORS[k][i]) ** 2 for i in range(3)))
    return name, "#%02x%02x%02x" % tuple(int(v) for v in px)


def data_uri(rgba: Image.Image, longest=420):
    scale = min(1.0, longest / max(rgba.size))
    if scale < 1.0:
        rgba = rgba.resize((max(1, int(rgba.width * scale)), max(1, int(rgba.height * scale))))
    buf = io.BytesIO(); rgba.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def use_gpu_detector():
    import torch
    from transformers import pipeline
    if eg._detector is None:
        eg._detector = pipeline("zero-shot-object-detection",
                                model="IDEA-Research/grounding-dino-tiny",
                                device=0 if torch.cuda.is_available() else -1)


CARD = """<article class="card">
  <div class="ph"><img src="{img}" alt="{name}"></div>
  <div class="meta">
    <div class="cat">{cat}</div>
    <div class="name">{color_cap} {name}</div>
    <div class="swatch"><span style="background:{hex}"></span>{color} · detected {score}%</div>
  </div>
</article>"""

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>My Wardrobe — Lovänya</title><style>
 *{{box-sizing:border-box;margin:0;padding:0}}
 body{{background:#fafafa;color:#1a1a1a;font-family:'Helvetica Neue',Arial,system-ui,sans-serif}}
 header{{padding:34px 24px 10px;text-align:center}}
 header h1{{font-size:26px;font-weight:800;letter-spacing:-.5px}}
 header p{{color:#8a8a8a;font-size:13px;margin-top:6px}}
 .src{{display:block;margin:16px auto 6px;max-width:150px;border-radius:12px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:18px;
   max-width:1040px;margin:18px auto 60px;padding:0 24px}}
 .card{{background:#fff;border:1px solid #ededed;border-radius:14px;overflow:hidden;
   transition:.15s;display:flex;flex-direction:column}}
 .card:hover{{box-shadow:0 12px 30px -16px rgba(0,0,0,.25);transform:translateY(-2px)}}
 .ph{{aspect-ratio:3/4;background:
   linear-gradient(135deg,#f7f7f7,#fff);display:flex;align-items:center;justify-content:center;padding:10px}}
 .ph img{{max-width:100%;max-height:100%;object-fit:contain}}
 .meta{{padding:12px 14px 16px}}
 .cat{{font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#b0b0b0}}
 .name{{font-size:14px;font-weight:600;margin:3px 0 8px;line-height:1.3}}
 .swatch{{font-size:11px;color:#8a8a8a;display:flex;align-items:center;gap:6px;text-transform:capitalize}}
 .swatch span{{width:13px;height:13px;border-radius:50%;border:1px solid #e0e0e0;display:inline-block}}
</style></head><body>
 <header><h1>My Wardrobe</h1>
 <p>{n} pieces extracted from one photo · Lovänya · on-device, no cloud</p>
 <img class="src" src="{src}" alt="source outfit"></header>
 <div class="grid">{cards}</div></body></html>"""


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python pipeline/scripts/wardrobe.py path/to/outfit.jpg")
    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"not found: {src}")
    OUTDIR.mkdir(parents=True, exist_ok=True)

    pil = Image.open(src).convert("RGB")
    use_gpu_detector()
    dets = eg.dedup(eg.detect(pil))

    # guards for hard photos (mirror selfie, hand-held phone):
    W, H = pil.size
    area = W * H
    def box_area(b):
        return (b[2] - b[0]) * (b[3] - b[1])
    def center(b):
        return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    def contains(outer, pt):
        return outer[0] <= pt[0] <= outer[2] and outer[1] <= pt[1] <= outer[3]
    kept = []
    for d in dets:
        # drop whole-person grabs (a single garment shouldn't cover the frame)
        if box_area(d["box"]) > 0.60 * area:
            print(f"  drop {d['cat']}/{d['label']}: whole-body box", flush=True); continue
        # a whole-outfit grab is BOTH large AND swallows other detections;
        # a wide real garment (open shirt) may overlap but isn't large
        swallowed = sum(1 for o in dets if o is not d and contains(d["box"], center(o["box"])))
        if box_area(d["box"]) > 0.42 * area and swallowed >= 2:
            print(f"  drop {d['cat']}/{d['label']}: whole-outfit (large + contains {swallowed})", flush=True); continue
        # kill phone/small false-positives that land as bag/accessory
        if d["cat"] in ("bag", "accessory") and d["score"] < 0.45:
            print(f"  drop {d['cat']}/{d['label']}: low-confidence ({d['score']:.2f})", flush=True); continue
        kept.append(d)
    dets = kept
    print(f"detected {len(dets)} garments", flush=True)

    cards = []
    for i, d in enumerate(dets):
        cut = sam2_cutout(pil, d["box"])
        cut.save(OUTDIR / f"item_{i}_{d['cat']}.png")
        color, hexv = dominant_color(cut)
        cards.append(CARD.format(
            img=data_uri(cut), name=NAME.get(d["cat"], d["label"].title()),
            cat=d["cat"], color=color, color_cap=color.title(), hex=hexv,
            score=round(d["score"] * 100),
        ))
        print(f"  item {i}: {color} {d['cat']} ({d['label']})", flush=True)

    html = PAGE.format(n=len(dets), src=data_uri(pil.convert("RGBA"), 300),
                       cards="\n".join(cards))
    out = OUTDIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"\nWrote {out}", flush=True)


if __name__ == "__main__":
    main()
