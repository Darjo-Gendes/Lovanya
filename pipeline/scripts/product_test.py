"""3-angle product-shot bake-off on already-extracted garment cutouts.

For each cutout: auto-derive attributes (category from filename, dominant color
from pixels — no judge re-run), then generate three angles and a side-by-side
HTML so we can pick the one closest to the real garment:
  A  Idealized  — txt2img from attributes (generic clean catalogue)
  B  Faithful   — img2img from the cutout, low strength (true to the real piece)
  C  Balanced   — img2img from the cutout, higher strength (flatter, cleaner)

Run from the repo root:
    python pipeline/scripts/product_test.py pipeline/review/wardrobe/item_1_top.png pipeline/review/wardrobe/item_2_bottom.png
"""
import base64
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image  # noqa: E402

from pipeline.app.product_shot import (  # noqa: E402
    product_shot, product_shot_from_ref,
)

OUTDIR = Path(__file__).resolve().parent.parent / "review" / "product"

# category (from cutout filename) -> garment noun for the prompt subject
CAT_NOUN = {
    "top": "long-sleeve top", "bottom": "wide-leg trousers", "dress": "dress",
    "outerwear": "shirt jacket", "shoes": "shoes", "bag": "handbag",
    "accessory": "accessory",
}
BASIC = {
    "black": (20, 20, 20), "white": (238, 238, 238), "grey": (128, 128, 128),
    "navy": (30, 40, 80), "blue": (60, 110, 200), "red": (200, 50, 50),
    "pink": (233, 130, 168), "green": (110, 150, 95), "beige": (215, 195, 165),
    "brown": (120, 85, 60), "cream": (240, 230, 205), "sage": (150, 165, 120),
}


def color_name(rgba: Image.Image) -> str:
    import numpy as np
    a = np.asarray(rgba.convert("RGBA"))
    m = a[..., 3] > 40
    if m.sum() == 0:
        return ""
    px = a[m][:, :3].mean(axis=0)
    r, g, b = px
    if min(r, g, b) > 200 and (max(r, g, b) - min(r, g, b)) < 22:
        return "white"
    return min(BASIC, key=lambda k: sum((px[i] - BASIC[k][i]) ** 2 for i in range(3)))


def attrs_from(path: Path):
    cat = path.stem.split("_")[-1]
    garment = CAT_NOUN.get(cat, "garment")
    color = color_name(Image.open(path))
    return garment, color


def uri(b, longest=300):
    im = b if isinstance(b, Image.Image) else Image.open(io.BytesIO(b))
    im = im.convert("RGBA")
    s = min(1.0, longest / max(im.size))
    if s < 1.0:
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    cutouts = [Path(p) for p in sys.argv[1:]]
    if not cutouts:
        sys.exit("give cutout PNG paths")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in cutouts:
        if not p.exists():
            print("skip missing", p); continue
        garment, color = attrs_from(p)
        cut = p.read_bytes()
        print(f"{p.name}: {color} {garment}", flush=True)

        t = time.time()
        a = product_shot(garment, color)                                   # idealized
        b = product_shot_from_ref(cut, garment, color, strength=0.45)      # faithful
        c = product_shot_from_ref(cut, garment, color, strength=0.68)      # balanced
        print(f"  3 angles in {time.time()-t:.0f}s", flush=True)
        for tag, data in [("A_idealized", a), ("B_faithful", b), ("C_balanced", c)]:
            (OUTDIR / f"{p.stem}_{tag}.png").write_bytes(data)

        rows.append(f"""<div class="row"><div class="lab">{color} {garment}</div>
          <div class="cells">
            <figure><img src="{uri(Image.open(p))}"><figcaption>cutout (real)</figcaption></figure>
            <figure><img src="{uri(a)}"><figcaption>A · idealized (txt2img)</figcaption></figure>
            <figure><img src="{uri(b)}"><figcaption>B · faithful (img2img .45)</figcaption></figure>
            <figure><img src="{uri(c)}"><figcaption>C · balanced (img2img .68)</figcaption></figure>
          </div></div>""")

    page = f"""<!doctype html><meta charset="utf-8"><style>
      body{{margin:0;background:#f4f4f4;font-family:'Helvetica Neue',Arial,sans-serif;color:#222}}
      h1{{padding:22px 26px 4px;font-size:20px}} .sub{{padding:0 26px 14px;color:#888;font-size:13px}}
      .row{{background:#fff;margin:14px 26px;border-radius:14px;padding:16px;box-shadow:0 10px 26px -20px rgba(0,0,0,.4)}}
      .lab{{font-size:11px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#b06;margin-bottom:10px}}
      .cells{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
      figure{{margin:0;text-align:center}}
      figure img{{width:100%;border-radius:10px;background:
        linear-gradient(45deg,#eee 25%,transparent 25%,transparent 75%,#eee 75%),
        linear-gradient(45deg,#eee 25%,#fff 25%,#fff 75%,#eee 75%);
        background-size:16px 16px;background-position:0 0,8px 8px}}
      figcaption{{font-size:11px;color:#777;margin-top:6px}}
    </style><h1>Product-shot bake-off — 3 angles</h1>
    <p class="sub">Real cutout vs three generation angles. Goal: closest to the real garment, flat on white.</p>
    {"".join(rows)}"""
    (OUTDIR / "index.html").write_text(page, encoding="utf-8")
    print(f"\nWrote {OUTDIR/'index.html'}", flush=True)


if __name__ == "__main__":
    main()
