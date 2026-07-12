"""Build the pipeline-comparison document: every approach we tried for the
worn-photo -> catalog-shot problem, on the same sample (b2_r1c4), side by side.

Self-contained HTML (base64 images) so it opens locally and survives OneDrive
dehydration. Nano Banana shots live only in AI Studio/chat, so that column is
represented by its verdict, not embedded pixels.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review"
OUT = REVIEW / "pipeline-comparison.html"
SAMPLE = "b2_r1c4"


def uri(path: Path, mx: int = 360) -> str | None:
    if not path.exists():
        return None
    im = Image.open(path)
    im.load()
    w, h = im.size
    sc = min(1.0, mx / max(w, h))
    if sc < 1.0:
        im = im.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def imgs(folder: Path, pat: str) -> list[str]:
    out = []
    for p in sorted(folder.glob(pat)):
        u = uri(p)
        if u:
            out.append(u)
    return out


# --- assemble each method's evidence -----------------------------------------
src = uri(ROOT / "samples" / f"{SAMPLE}.jpg", 300)

METHODS = [
    {
        "n": "1", "name": "GroundingDINO + SAM2 + SDXL",
        "type": "Local · on-GPU · $0",
        "imgs": imgs(REVIEW / "garments" / "shots", f"{SAMPLE}_*_shot.png"),
        "quality": "Failed", "cost": "$0", "speed": "~30 s/img",
        "status": "bad",
        "verdict": "Detect box -> segment -> img2img polish. Faithful img2img kept the "
                   "WEARER (person on white), not a flat garment; detection cut non-garments "
                   "(a pillow became \"trousers\") and missed layers. Stage errors compounded.",
    },
    {
        "n": "2", "name": "Nano Banana (Gemini 2.5 Flash Image)",
        "type": "Cloud · paid",
        "imgs": [],  # user-generated in AI Studio, not on disk
        "quality": "Excellent", "cost": "~$0.04/img (~$4 / 20 outfits)", "speed": "~12 s/img",
        "status": "good",
        "verdict": "Single generative call reconstructs each garment as a flat catalog shot. "
                   "User-validated as the quality benchmark (hijab, blazer, shirt, trousers, bag "
                   "all correct). Blocker: free tier has 0 image quota -> needs billing. "
                   "Images live in AI Studio / this chat, not on disk.",
    },
    {
        "n": "3", "name": "Qwen-Image-Edit 20B (GGUF)",
        "type": "Local · on-GPU · $0",
        "imgs": imgs(REVIEW / "garments_gemini" / "local_qwen_lightning", f"{SAMPLE}_*.png")[:6],
        "quality": "Failed", "cost": "$0", "speed": "74 s (8-step) / 316 s (20-step)",
        "status": "bad",
        "verdict": "Instruction editor, benchmarked against Nano Banana. Its training goal is "
                   "\"preserve the input, edit minimally\" - so it returned the ORIGINAL selfie "
                   "nearly verbatim instead of extracting garments. Wrong architecture for "
                   "extraction; 8 GB forced Q3 + shrunken views that made it worse.",
    },
    {
        "n": "4a", "name": "Qwen3-VL + FLUX — v1 (single-pass)",
        "type": "Local · on-GPU · $0",
        "imgs": imgs(REVIEW / "garments_flux" / "shots_v1", f"{SAMPLE}_*.png"),
        "quality": "Catalog-grade", "cost": "$0", "speed": "~4.5 min/img",
        "status": "good",
        "verdict": "One vision pass -> free description -> FLUX. 3/4 catalog-grade first try, "
                   "zero false positives. But the text bottleneck lost shape truth: bag rendered "
                   "portrait (never said \"landscape\"), coat mislabeled \"trench\", colors warm-"
                   "cast (cream read as beige), and recall was 4/6 (missed occluded trousers + watch).",
    },
    {
        "n": "4b", "name": "Qwen3-VL + FLUX — v2 (two-pass + archetypes)",
        "type": "Local · on-GPU · $0",
        "imgs": imgs(REVIEW / "garments_flux" / "shots", f"{SAMPLE}_*.png"),
        "quality": "Catalog-grade", "cost": "$0", "speed": "~4.5 min/img (8 GB spill)",
        "status": "good",
        "verdict": "Pass 1 detects garments + boxes (recall 5/6 - recovered the occluded "
                   "trousers); pass 2 zooms each crop + sees the full photo, fills a category "
                   "checklist, snaps to an archetype from garment-archetypes.md. Fixed: coat -> "
                   "correct \"longline blazer\", warm-cast colors (cream not beige), bag body vs "
                   "strap. Hijab now on a featureless mannequin head (worn drape). REMAINING LIMIT: "
                   "FLUX still rendered the bag PORTRAIT despite the description saying \"landscape, "
                   "wider than tall\" - text can't override FLUX's geometry prior. That needs "
                   "silhouette conditioning (ControlNet), the phase-2 lever.",
    },
    {
        "n": "5", "name": "OminiControl: SAM2 pixels -> subject-conditioned FLUX",
        "type": "Local · on-GPU · $0",
        "imgs": imgs(REVIEW / "garments_omini" / "shots", f"{SAMPLE}_*.png"),
        "quality": "Very good", "cost": "$0", "speed": "~24 s/img, 5.8GB peak",
        "status": "good",
        "verdict": "The image-conditioned breakthrough: the garment's SAM2 cutout enters FLUX "
                   "as condition tokens (OminiControl subject LoRA, +0.1% params, via the mmgp "
                   "GPU-poor recipe: profile 5 + int8). The bag FINALLY rendered landscape "
                   "box-flap - the geometry text could never enforce - at 10x the speed of "
                   "text-only FLUX with no VRAM spill. Remaining gap vs Nano Banana: color/"
                   "hardware fidelity, traceable to the 245px source thumbnails, not the "
                   "architecture. Stack: Qwen3-VL two-pass describe -> SAM2 cutout -> "
                   "OminiControl+schnell. All local, Apache-friendly.",
    },
]

SUMMARY = [
    ("Approach", "Where", "Quality", "Cost/img", "Speed", "Verdict"),
    ("1 · DINO+SAM2+SDXL", "Local", "Failed", "$0", "~30 s", "Kept the wearer; false positives"),
    ("2 · Nano Banana", "Cloud", "Excellent", "~$0.04", "~12 s", "Best quality; costs money at scale"),
    ("3 · Qwen-Image-Edit", "Local", "Failed", "$0", "74-316 s", "Copies the input (editor bias)"),
    ("4a · Qwen3-VL+FLUX v1", "Local", "Catalog-grade", "$0", "~4.5 min", "Works; shape/color/recall gaps"),
    ("4b · +two-pass+archetypes", "Local", "Catalog-grade", "$0", "~4.5 min", "Recall+color fixed; text can't force geometry"),
    ("5 · +OminiControl pixels", "Local", "Very good", "$0", "~24 s", "Geometry obeys the reference pixels; the local winner"),
]


def card(m: dict) -> str:
    if m["imgs"]:
        thumbs = "".join(f'<img src="{u}">' for u in m["imgs"])
        gallery = f'<div class=gal>{thumbs}</div>'
    else:
        gallery = ('<div class=gal><div class=noimg>images generated in AI Studio<br>'
                   '(not stored on disk)</div></div>')
    return f"""<section class="card {m['status']}">
      <div class=head><span class=num>{m['n']}</span>
        <div><h3>{m['name']}</h3><span class=type>{m['type']}</span></div>
        <span class="badge {m['status']}">{m['quality']}</span></div>
      {gallery}
      <div class=meta><span><b>Cost</b> {m['cost']}</span><span><b>Speed</b> {m['speed']}</span></div>
      <p class=verdict>{m['verdict']}</p>
    </section>"""


rows = "".join(
    "<tr>" + "".join(f"<{'th' if i == 0 else 'td'}>{c}</{'th' if i == 0 else 'td'}>"
                     for c in r) + "</tr>"
    for i, r in enumerate(SUMMARY))

CSS = """
*{box-sizing:border-box}body{margin:0;background:#f4f3f2;color:#1c1714;
font-family:Helvetica Neue,Arial,sans-serif;line-height:1.5}
.wrap{max-width:1100px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:28px;font-weight:800;margin:0 0 4px}
.lead{color:#8a807b;font-size:14px;margin:0 0 28px}
.source{background:#fff;border-radius:16px;padding:18px;display:flex;gap:20px;align-items:center;
box-shadow:0 14px 34px -24px rgba(80,40,50,.5);margin-bottom:14px}
.source img{width:150px;border-radius:12px;flex:none}
.source h2{margin:0 0 6px;font-size:16px}.source p{margin:0;font-size:13px;color:#6b625d}
.goal{background:#fbeef2;border:1px solid #f3d7e0;border-radius:12px;padding:12px 16px;
font-size:13px;color:#8a5060;margin-bottom:26px}
.card{background:#fff;border-radius:16px;padding:20px;margin-bottom:18px;
box-shadow:0 14px 34px -24px rgba(80,40,50,.5);border-left:5px solid #ccc}
.card.good{border-left-color:#3f9d6d}.card.bad{border-left-color:#cf5c5c}
.head{display:flex;align-items:center;gap:14px;margin-bottom:14px}
.num{width:30px;height:30px;border-radius:50%;background:#1c1714;color:#fff;font-weight:700;
display:flex;align-items:center;justify-content:center;flex:none}
.head h3{margin:0;font-size:17px}.type{font-size:12px;color:#8a807b}
.badge{margin-left:auto;font-size:11px;font-weight:700;padding:4px 12px;border-radius:20px}
.badge.good{background:#e3f4ea;color:#2c7a52}.badge.bad{background:#fbe4e4;color:#b33}
.gal{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.gal img{width:130px;height:130px;object-fit:contain;border-radius:10px;background:#fafafa;border:1px solid #eee}
.noimg{width:100%;padding:26px;text-align:center;color:#b9b0ab;font-size:12px;
background:#faf8f7;border:1px dashed #e2dad6;border-radius:10px}
.meta{display:flex;gap:22px;font-size:12.5px;color:#6b625d;margin-bottom:10px}
.meta b{color:#1c1714}
.verdict{font-size:13px;color:#4a423e;margin:0}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:14px;overflow:hidden;
box-shadow:0 14px 34px -24px rgba(80,40,50,.5);font-size:13px;margin-top:26px}
th,td{padding:11px 13px;text-align:left;border-bottom:1px solid #f0ebe8}
th{background:#1c1714;color:#fff;font-size:12px}tr:last-child td{border-bottom:none}
.foot{margin-top:26px;font-size:13px;color:#6b625d}
.foot b{color:#1c1714}
"""

html = f"""<!doctype html><meta charset=utf-8>
<title>Lovanya garment pipeline - every approach compared</title>
<style>{CSS}</style>
<div class=wrap>
<h1>Garment product-shot pipeline: every approach compared</h1>
<p class=lead>Same sample ({SAMPLE}), four methods, honest verdicts. Built 2026-07-11.</p>

<div class=source>
  <img src="{src}">
  <div><h2>The source: one worn-outfit photo</h2>
  <p>An 8&nbsp;KB cropped mirror selfie - taupe hijab, beige longline blazer, white shirt,
  white trousers, dark brown shoulder bag, phone in hand. Every output below is derived
  from this single image.</p></div>
</div>
<div class=goal><b>The goal:</b> turn a worn-outfit photo into a clean, Uniqlo-style
flat product shot for <i>each</i> garment - accurately, cheaply, at scale.</div>

{"".join(card(m) for m in METHODS)}

<table>{rows}</table>

<p class=foot><b>Where we landed:</b> Approach 4 (Qwen3-VL + FLUX) is the working local,
zero-cost pipeline - quality validated on this sample. Nano Banana (2) still wins on raw
quality and speed but costs money and needs billing enabled. The two open items on Approach 4
are speed (the 12B FLUX spills the 8&nbsp;GB card at ~4.5&nbsp;min/image) and detection recall
(4 of 6 garments; the occluded trousers and watch were missed).</p>
</div>"""

OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT}  ({len(html)/1e6:.2f} MB)")
for m in METHODS:
    print(f"  method {m['n']}: {len(m['imgs'])} images embedded")
