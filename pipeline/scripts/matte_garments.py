"""GPU per-garment cutouts: the fair test the UI-PC couldn't run on CPU.

For each outfit photo:  GroundingDINO detects each garment (GPU) -> tight crop
per garment -> BiRefNet mattes each crop (GPU) -> transparent cutout. Writes
per-garment PNGs + a self-contained HTML preview so the pixels decide.

This resolves review/README.md finding #3/#4: whole-photo matting wasn't the
bottleneck; the per-garment crop is. Here we matte the tight crops directly.

Run from the repo root:
    python pipeline/scripts/matte_garments.py [--n 5] [samples/x.jpg ...]
"""

import argparse
import base64
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_garments as eg  # noqa: E402 — reuse its proven detect/dedup/crop

PIPELINE = Path(__file__).resolve().parent.parent
SAMPLES = PIPELINE / "samples"
OUTDIR = PIPELINE / "review" / "matte_gpu"

_birefnet = None
_bire_tf = None


def use_gpu_detector():
    """Point extract_garments' detector at the GPU (it defaults to CPU)."""
    import torch
    from transformers import pipeline
    if eg._detector is None:
        eg._detector = pipeline(
            "zero-shot-object-detection",
            model="IDEA-Research/grounding-dino-tiny",
            device=0 if torch.cuda.is_available() else -1,
        )


def birefnet_cut(pil: Image.Image) -> Image.Image:
    """Matte one crop with BiRefNet on the GPU (fp16)."""
    global _birefnet, _bire_tf
    import torch
    from torchvision import transforms
    from transformers import AutoModelForImageSegmentation
    if _birefnet is None:
        print("  loading BiRefNet (ZhengPeng7/BiRefNet, GPU fp16)…", flush=True)
        m = AutoModelForImageSegmentation.from_pretrained(
            "ZhengPeng7/BiRefNet", trust_remote_code=True
        )
        _birefnet = m.to("cuda").half().eval() if torch.cuda.is_available() else m.float().eval()
        _bire_tf = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    cuda = torch.cuda.is_available()
    inp = _bire_tf(pil).unsqueeze(0)
    inp = inp.to("cuda").half() if cuda else inp
    with torch.no_grad():
        pred = _birefnet(inp)[-1].sigmoid().float().cpu()[0].squeeze()
    mask = transforms.ToPILImage()(pred).resize(pil.size)
    out = pil.convert("RGBA")
    out.putalpha(mask)
    return out


def detect_garments(pil: Image.Image):
    """Return [(category_label, crop_image)] using extract_garments' proven
    detection + per-category NMS dedup, on the GPU."""
    use_gpu_detector()
    dets = eg.dedup(eg.detect(pil))
    return [(f'{d["cat"]}·{d["label"]}', eg.crop_box(pil, d["box"])) for d in dets]


def opaque_pct(rgba: Image.Image) -> float:
    import numpy as np
    a = np.asarray(rgba.split()[-1])
    return round(100 * (a > 32).mean(), 1)


def thumb(pil: Image.Image, longest=240) -> str:
    scale = min(1.0, longest / max(pil.size))
    if scale < 1.0:
        pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))))
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="*")
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    def resolve(p: str) -> Path:
        for cand in (Path(p), PIPELINE / p, SAMPLES / Path(p).name):
            if cand.exists():
                return cand
        return Path(p)  # non-existent; reported as skip below

    if args.images:
        photos = [resolve(p) for p in args.images]
    else:
        import random
        pool = sorted(SAMPLES.glob("*.jpg"))
        random.seed(7)
        photos = random.sample(pool, min(args.n, len(pool)))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for p in photos:
        if not p.exists():
            print(f"  skip (missing): {p.name}", flush=True)
            continue
        pil = Image.open(p).convert("RGB")
        t0 = time.time()
        garments = detect_garments(pil)
        cells = []
        for i, (lab, crop) in enumerate(garments):
            cut = birefnet_cut(crop)
            safe = lab.replace("·", "_").replace(" ", "")
            cut.save(OUTDIR / f"{p.stem}_{i}_{safe}.png")
            cells.append(
                f'<div class="g"><div class="cut"><img src="{thumb(cut)}"></div>'
                f'<div class="cap">{lab} · {opaque_pct(cut)}% kept</div></div>'
            )
        dt = time.time() - t0
        rows.append(
            f'<div class="row"><div class="name">{p.name} · {len(garments)} garments · {dt:.0f}s</div>'
            f'<div class="orig"><img src="{thumb(pil)}"></div>'
            f'<div class="grid">{"".join(cells)}</div></div>'
        )
        print(f"  {p.name}: {len(garments)} garments in {dt:.0f}s "
              f"({', '.join(l for l, _ in garments)})", flush=True)

    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>GPU per-garment cutouts — BiRefNet on tight crops</title><style>
 body{{margin:0;background:#e8dada;font-family:system-ui,Segoe UI,sans-serif;color:#6e5a5a}}
 .wrap{{max-width:1000px;margin:0 auto;padding:24px 16px 60px}}
 h1{{font-family:Georgia,serif;color:#48292e;font-size:23px;margin:0 0 4px}}
 .lede{{font-size:13px;margin:0 0 18px;max-width:680px}}
 .row{{background:#fff;border-radius:18px;padding:16px;margin:14px 0;
   box-shadow:0 14px 32px -22px rgba(206,140,150,.55);position:relative}}
 .name{{position:absolute;top:-9px;left:16px;background:#ce6e86;color:#fff;font-size:10px;
   font-weight:600;padding:2px 10px;border-radius:10px}}
 .row{{display:grid;grid-template-columns:200px 1fr;gap:16px;align-items:start}}
 .orig img{{width:100%;border-radius:12px}}
 .grid{{display:flex;flex-wrap:wrap;gap:12px}}
 .g{{width:150px;text-align:center}}
 .cut{{background:linear-gradient(45deg,#eee 25%,transparent 25%,transparent 75%,#eee 75%),
   linear-gradient(45deg,#eee 25%,#fff 25%,#fff 75%,#eee 75%);
   background-size:16px 16px;background-position:0 0,8px 8px;border-radius:12px}}
 .cut img{{width:100%;border-radius:12px;display:block}}
 .cap{{font-size:10px;font-weight:600;letter-spacing:.5px;margin-top:5px;color:#6e8a4e}}
</style></head><body><div class="wrap">
 <h1>GPU per-garment cutouts — BiRefNet on tight crops</h1>
 <p class="lede">Each outfit photo → GroundingDINO detects each garment → the tight
 crop is matted by BiRefNet on the 4060&nbsp;Ti. This is the per-garment test the
 UI-PC couldn't run on CPU. Checkerboard = transparent; "% kept" = opaque pixels.</p>
 {"".join(rows)}
</div></body></html>"""
    (OUTDIR / "index.html").write_text(page, encoding="utf-8")
    print(f"\nWrote {OUTDIR / 'index.html'}", flush=True)


if __name__ == "__main__":
    main()
