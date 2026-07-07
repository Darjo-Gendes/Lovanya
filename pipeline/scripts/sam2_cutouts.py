"""Box-prompted SAM2 garment cutouts, and a side-by-side vs BiRefNet.

Per garment: GroundingDINO box (reused from extract_garments) -> SAM2 mask ->
clean cutout. Writes PNGs + an HTML preview so the pixels decide whether SAM2
fixes the 'kept the person' problem BiRefNet had.

Run from the repo root:
    python pipeline/scripts/sam2_cutouts.py samples/sample_r1c5.jpg samples/b4_r4c4.jpg
"""
import base64
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

import extract_garments as eg  # noqa: E402
from pipeline.app.cutout import sam2_cutout  # noqa: E402

PIPELINE = Path(__file__).resolve().parent.parent
SAMPLES = PIPELINE / "samples"
OUTDIR = PIPELINE / "review" / "sam2"


def use_gpu_detector():
    import torch
    from transformers import pipeline
    if eg._detector is None:
        eg._detector = pipeline("zero-shot-object-detection",
                                model="IDEA-Research/grounding-dino-tiny",
                                device=0 if torch.cuda.is_available() else -1)


def opaque_pct(rgba):
    import numpy as np
    a = np.asarray(rgba.split()[-1])
    return round(100 * (a > 32).mean(), 1)


def thumb(pil, longest=240):
    scale = min(1.0, longest / max(pil.size))
    if scale < 1.0:
        pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))))
    buf = io.BytesIO(); pil.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def resolve(p):
    for c in (Path(p), PIPELINE / p, SAMPLES / Path(p).name):
        if c.exists():
            return c
    return Path(p)


def main():
    photos = [resolve(a) for a in sys.argv[1:]] or [SAMPLES / "sample_r1c5.jpg", SAMPLES / "b4_r4c4.jpg"]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    use_gpu_detector()
    rows = []
    for p in photos:
        if not p.exists():
            print(f"  skip (missing): {p.name}", flush=True); continue
        pil = Image.open(p).convert("RGB")
        t0 = time.time()
        dets = eg.dedup(eg.detect(pil))
        cells = []
        for i, d in enumerate(dets):
            cut = sam2_cutout(pil, d["box"])
            cut.save(OUTDIR / f"{p.stem}_{i}_{d['cat']}_{d['label']}.png".replace(" ", ""))
            cells.append(f'<div class="g"><div class="cut"><img src="{thumb(cut)}"></div>'
                         f'<div class="cap">{d["cat"]}·{d["label"]} · {opaque_pct(cut)}% kept</div></div>')
        dt = time.time() - t0
        rows.append(f'<div class="row"><div class="name">{p.name} · {len(dets)} garments · {dt:.0f}s</div>'
                    f'<div class="orig"><img src="{thumb(pil)}"></div>'
                    f'<div class="grid">{"".join(cells)}</div></div>')
        print(f"  {p.name}: {len(dets)} garments in {dt:.0f}s", flush=True)

    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>SAM2 box-prompted cutouts</title><style>
 body{{margin:0;background:#e8dada;font-family:system-ui,Segoe UI,sans-serif;color:#6e5a5a}}
 .wrap{{max-width:1000px;margin:0 auto;padding:24px 16px 60px}}
 h1{{font-family:Georgia,serif;color:#48292e;font-size:23px;margin:0 0 4px}}
 .lede{{font-size:13px;margin:0 0 18px;max-width:680px}}
 .row{{background:#fff;border-radius:18px;padding:16px;margin:14px 0;position:relative;
   box-shadow:0 14px 32px -22px rgba(206,140,150,.55);display:grid;grid-template-columns:200px 1fr;gap:16px}}
 .name{{position:absolute;top:-9px;left:16px;background:#ce6e86;color:#fff;font-size:10px;font-weight:600;padding:2px 10px;border-radius:10px}}
 .orig img{{width:100%;border-radius:12px}}
 .grid{{display:flex;flex-wrap:wrap;gap:12px}} .g{{width:150px;text-align:center}}
 .cut{{background:linear-gradient(45deg,#eee 25%,transparent 25%,transparent 75%,#eee 75%),
   linear-gradient(45deg,#eee 25%,#fff 25%,#fff 75%,#eee 75%);background-size:16px 16px;background-position:0 0,8px 8px;border-radius:12px}}
 .cut img{{width:100%;border-radius:12px;display:block}} .cap{{font-size:10px;font-weight:600;margin-top:5px;color:#6e8a4e}}
</style></head><body><div class="wrap">
 <h1>SAM2 box-prompted garment cutouts</h1>
 <p class="lede">GroundingDINO box -> SAM2 mask -> cutout. Unlike BiRefNet (which kept the
 person), SAM2 masks the exact garment. Checkerboard = transparent.</p>
 {"".join(rows)}</div></body></html>"""
    (OUTDIR / "index.html").write_text(page, encoding="utf-8")
    print(f"\nWrote {OUTDIR / 'index.html'}", flush=True)


if __name__ == "__main__":
    main()
