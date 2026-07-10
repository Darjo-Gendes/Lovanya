"""AFK phase 2 — Uniqlo-style product shots from the phase-1 cutouts.

Reads review/garments/manifest.jsonl, renders each cutout via the steady
product-shot format (SDXL img2img), writes shots + a review HTML grouping each
sample's cutouts and shots side by side.
"""
import base64
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image  # noqa: E402

from pipeline.app.product_shot import product_shot_from_ref  # noqa: E402

PIPELINE = Path(__file__).resolve().parent.parent
OUT = PIPELINE / "review" / "garments"
SHOTS = OUT / "shots"
SAMPLES = PIPELINE / "samples"


def uri(path_or_im, longest=260):
    im = path_or_im if isinstance(path_or_im, Image.Image) else Image.open(path_or_im)
    im = im.convert("RGBA")
    s = min(1.0, longest / max(im.size))
    if s < 1.0:
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    manifest = [json.loads(l) for l in (OUT / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"rendering {len(manifest)} product shots…", flush=True)

    by_sample = {}
    for n, m in enumerate(manifest, 1):
        t = time.time()
        try:
            shot = product_shot_from_ref(Path(m["cutout"]).read_bytes(),
                                         m["garment"], m["color"], strength=0.5, seed=7)
            sp = SHOTS / (Path(m["cutout"]).stem + "_shot.png")
            sp.write_bytes(shot)
            m["shot"] = str(sp)
        except Exception as e:
            m["shot"] = None
            print(f"  [{n}] {Path(m['cutout']).name} FAILED: {type(e).__name__}", flush=True)
        by_sample.setdefault(m["sample"], []).append(m)
        print(f"  [{n}/{len(manifest)}] {m['color']} {m['garment']} in {time.time()-t:.0f}s", flush=True)

    # review HTML
    rows = []
    for sample, items in by_sample.items():
        cells = []
        for m in items:
            shot = f'<img src="{uri(m["shot"])}">' if m.get("shot") else '<div class="fail">render failed</div>'
            cells.append(f"""<div class="pair">
              <figure><img class="cut" src="{uri(m['cutout'])}"><figcaption>{m['color']} {m['garment']} · cutout</figcaption></figure>
              <figure><div class="pshot">{shot}</div><figcaption>product shot</figcaption></figure>
            </div>""")
        rows.append(f"""<section class="samp"><div class="tag">{sample}</div>
          <img class="src" src="{uri(SAMPLES / sample, 150)}">
          <div class="pairs">{"".join(cells)}</div></section>""")

    page = f"""<!doctype html><meta charset="utf-8"><title>Garment cutting — Uniqlo style</title><style>
      body{{margin:0;background:#f4f3f2;font-family:'Helvetica Neue',Arial,sans-serif;color:#1c1714}}
      h1{{padding:24px 28px 2px;font-size:22px;font-weight:800}}
      .sub{{padding:0 28px 16px;color:#8a807b;font-size:13px}}
      .samp{{background:#fff;margin:16px 28px;border-radius:16px;padding:18px 18px 20px;position:relative;
        box-shadow:0 14px 34px -24px rgba(80,40,50,.5);display:grid;grid-template-columns:150px 1fr;gap:20px;align-items:start}}
      .tag{{position:absolute;top:-9px;left:20px;background:#cf5c7e;color:#fff;font-size:10px;font-weight:700;padding:2px 10px;border-radius:9px}}
      .src{{width:100%;border-radius:12px}}
      .pairs{{display:flex;flex-wrap:wrap;gap:22px}}
      .pair{{display:flex;gap:10px}}
      figure{{margin:0;width:130px;text-align:center}}
      figure img,.pshot{{width:130px;height:162px;object-fit:contain;border-radius:10px;background:
        linear-gradient(45deg,#eee 25%,transparent 25%,transparent 75%,#eee 75%),
        linear-gradient(45deg,#eee 25%,#fff 25%,#fff 75%,#eee 75%);background-size:14px 14px;background-position:0 0,7px 7px}}
      .pshot{{display:flex;align-items:center;justify-content:center;background:#fff;border:1px solid #eee}}
      .pshot img{{width:100%;height:100%;object-fit:contain;background:none}}
      figcaption{{font-size:10.5px;color:#8a807b;margin-top:5px}}
      .fail{{font-size:11px;color:#c05;display:flex;align-items:center;justify-content:center;height:100%}}
    </style><h1>Garment cutting — Uniqlo style</h1>
    <p class="sub">{len(manifest)} garments from 20 random outfits: SAM2 cutout → SDXL product shot on white. All local, zero tokens.</p>
    {"".join(rows)}"""
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"SHOT PHASE DONE: wrote {OUT/'index.html'}", flush=True)


if __name__ == "__main__":
    main()
