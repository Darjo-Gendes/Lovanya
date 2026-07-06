"""Apples-to-apples matting bake-off: rembg (what we used) vs BiRefNet (the
2024 SOTA candidate), on the SAME sample photos. Builds a side-by-side HTML so
the real pixels decide — no hand-waving.

CPU-only (this laptop). BiRefNet downloads ~once (trust_remote_code loads the
official ZhengPeng7/BiRefNet repo). On the 4060 Ti this is ~1-2s/image; here it
is slow but only needs to run once for the comparison.

Usage (from repo root):
    python pipeline/scripts/simulate_birefnet.py
"""
from __future__ import annotations

import base64
import io
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from PIL import Image

PIPELINE = Path(__file__).resolve().parent.parent
SAMPLES = PIPELINE / "samples"
OUTDIR = PIPELINE / "review" / "birefnet"

# The same 5 the extraction ran on, so the comparison is fair.
PHOTOS = ["b4_r4c4.jpg", "b2_r3c3.jpg", "b2_r1c4.jpg", "sample_r1c5.jpg", "b3_r1c6.jpg"]

_birefnet = None
_bire_tf = None
_rembg_session = None


def rembg_cut(pil: Image.Image) -> Image.Image:
    global _rembg_session
    from rembg import new_session, remove
    if _rembg_session is None:
        _rembg_session = new_session("u2net")
    return remove(pil, session=_rembg_session).convert("RGBA")


def birefnet_cut(pil: Image.Image) -> Image.Image:
    global _birefnet, _bire_tf
    import torch
    from torchvision import transforms
    from transformers import AutoModelForImageSegmentation
    if _birefnet is None:
        print("  loading BiRefNet (ZhengPeng7/BiRefNet, CPU)…", flush=True)
        _birefnet = AutoModelForImageSegmentation.from_pretrained(
            "ZhengPeng7/BiRefNet", trust_remote_code=True
        )
        _birefnet = _birefnet.float()  # checkpoint ships fp16; CPU needs fp32
        _birefnet.eval()
        _bire_tf = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    inp = _bire_tf(pil).unsqueeze(0)
    with torch.no_grad():
        pred = _birefnet(inp)[-1].sigmoid().cpu()[0].squeeze()
    mask = transforms.ToPILImage()(pred).resize(pil.size)
    out = pil.copy().convert("RGBA")
    out.putalpha(mask)
    return out


def thumb(pil: Image.Image, longest=300) -> str:
    scale = min(1.0, longest / max(pil.size))
    if scale < 1.0:
        pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))))
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


ROW = """<div class="row">
  <div class="col"><div class="lab orig">original</div><img src="{orig}"></div>
  <div class="col"><div class="lab bad">rembg (u2net) · {rt:.0f}s</div><div class="cut"><img src="{rem}"></div></div>
  <div class="col"><div class="lab good">BiRefNet · {bt:.0f}s</div><div class="cut"><img src="{bir}"></div></div>
  <div class="name">{name}</div>
</div>"""

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Matting bake-off — rembg vs BiRefNet</title><style>
 body{{margin:0;background:#e8dada;font-family:'Poppins',system-ui,Segoe UI,sans-serif;color:#6e5a5a}}
 .wrap{{max-width:900px;margin:0 auto;padding:24px 16px 60px}}
 h1{{font-family:Georgia,serif;color:#48292e;font-size:24px;margin:0 0 4px}}
 .lede{{font-size:13px;margin:0 0 18px;max-width:640px}}
 .row{{background:#fff;border-radius:18px;padding:14px;margin:14px 0;box-shadow:0 14px 32px -22px rgba(206,140,150,.55);
   display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;position:relative}}
 .col{{text-align:center}} .col img{{width:100%;border-radius:12px;display:block}}
 .cut{{background:linear-gradient(45deg,#eee 25%,transparent 25%,transparent 75%,#eee 75%),
   linear-gradient(45deg,#eee 25%,#fff 25%,#fff 75%,#eee 75%);background-size:16px 16px;background-position:0 0,8px 8px;border-radius:12px}}
 .lab{{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;margin-bottom:5px}}
 .orig{{color:#a2908f}} .bad{{color:#c0555f}} .good{{color:#6e8a4e}}
 .name{{position:absolute;top:-9px;left:14px;background:#ce6e86;color:#fff;font-size:10px;font-weight:600;
   padding:2px 10px;border-radius:10px}}
</style></head><body><div class="wrap">
 <h1>Matting bake-off: rembg vs BiRefNet</h1>
 <p class="lede">Same photo, two background removers. <b>rembg (u2net)</b> is what made our garment cutouts faint;
 <b>BiRefNet</b> is the 2024 SOTA candidate — free, self-hostable, fits your 8&nbsp;GB card. Checkerboard = transparent.</p>
 {rows}
</div></body></html>"""


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in PHOTOS:
        p = SAMPLES / name
        if not p.exists():
            print(f"  skip (missing): {name}", flush=True)
            continue
        pil = Image.open(p).convert("RGB")
        t0 = time.time(); rem = rembg_cut(pil); rt = time.time() - t0
        t1 = time.time(); bir = birefnet_cut(pil); bt = time.time() - t1
        rem.save(OUTDIR / f"{p.stem}_rembg.png")
        bir.save(OUTDIR / f"{p.stem}_birefnet.png")
        rows.append(ROW.format(orig=thumb(pil), rem=thumb(rem), bir=thumb(bir),
                               rt=rt, bt=bt, name=name))
        print(f"  {name}: rembg {rt:.0f}s · BiRefNet {bt:.0f}s", flush=True)
    (OUTDIR / "index.html").write_text(PAGE.format(rows="\n".join(rows)), encoding="utf-8")
    print(f"\nWrote {OUTDIR / 'index.html'}")


if __name__ == "__main__":
    main()
