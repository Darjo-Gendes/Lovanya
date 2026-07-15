"""Visual page for the FashionSigLIP test: each generated garment shot, its
match score, and the user's vote — sorted by score so the (lack of)
correlation is visible at a glance. Self-contained (base64), opens locally.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review" / "garments_omini"
SHOTS = OUT / "shots"
CONDS = OUT / "conditions"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
RATINGS = Path("C:/Users/USER/Downloads/garment-ratings (2).json")
PAGE = OUT / "fashionqa-visual.html"


def thumb(path: Path, mx: int = 300) -> str:
    im = Image.open(path); im.load()
    w, h = im.size; sc = min(1.0, mx / max(w, h))
    if sc < 1.0:
        im = im.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    qa = json.loads((OUT / "fashion_qa.json").read_text(encoding="utf-8"))
    ratings = {r["id"]: r for r in json.loads(RATINGS.read_text(encoding="utf-8"))["results"]}
    rows = []
    for sid, r in ratings.items():
        shot = SHOTS / f"{sid}.png"
        if sid not in qa or not shot.exists():
            continue
        cond = CONDS / f"{sid}.png"
        rows.append({
            "score": qa[sid]["match"], "rating": r["rating"],
            "archetype": r.get("archetype", ""), "category": r.get("category", ""),
            "color": r.get("color", ""), "note": r.get("note", ""), "sid": sid,
            "render": thumb(shot), "src": thumb(cond) if cond.exists() else "",
        })
    rows.sort(key=lambda x: x["score"])
    downs = [i for i, r in enumerate(rows, 1) if r["rating"] == "down"]

    cards = []
    for i, r in enumerate(rows, 1):
        cls = "card " + r["rating"]
        srcimg = f'<img class=src src="{r["src"]}" title="source cutout">' if r["src"] else ""
        note = f'<div class=note>{r["note"]}</div>' if r["note"] else ""
        cards.append(f"""<div class="{cls}">
          <div class=rank>#{i}</div>
          <div class=imgs><img class=render src="{r['render']}" title="generated shot">{srcimg}</div>
          <div class=score>{r['score']:.3f}</div>
          <div class=vote>{'👎 DOWN' if r['rating']=='down' else '👍 up'}</div>
          <div class=meta><b>{r['archetype']}</b><span>{r['category']}</span></div>
          {note}
        </div>""")

    css = """
    body{margin:0;background:#f4f3f2;color:#1c1714;font-family:Helvetica Neue,Arial,sans-serif}
    .hd{padding:20px 26px;background:#1c1714;color:#fff}
    .hd h1{margin:0 0 6px;font-size:19px}
    .hd p{margin:2px 0;font-size:13px;opacity:.9}
    .hd b{color:#f2b8cc}
    .legend{padding:12px 26px;font-size:12.5px;color:#6b625d;background:#fbeef2;border-bottom:1px solid #f3d7e0}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:14px;padding:18px 26px 60px}
    .card{background:#fff;border-radius:12px;padding:10px;position:relative;border-left:5px solid #ccc;
    box-shadow:0 10px 26px -20px rgba(80,40,50,.6)}
    .card.up{border-left-color:#3f9d6d}.card.down{border-left-color:#cf5c5c}
    .rank{position:absolute;top:8px;left:10px;font-size:11px;font-weight:800;color:#b9b0ab}
    .imgs{display:flex;gap:5px;align-items:center;justify-content:center;margin:6px 0}
    .render{width:120px;height:120px;object-fit:contain;border-radius:8px;background:#fafafa}
    .src{width:44px;height:44px;object-fit:contain;border-radius:5px;background:#f0f0f0;border:1px solid #eee;opacity:.85}
    .score{font-size:22px;font-weight:800;text-align:center;letter-spacing:-.5px}
    .vote{text-align:center;font-size:12px;font-weight:700;margin-top:2px}
    .card.up .vote{color:#2c7a52}.card.down .vote{color:#b33}
    .meta{font-size:11px;color:#4a423e;margin-top:6px;line-height:1.35;text-align:center}
    .meta span{display:block;font-size:9.5px;color:#b9b0ab;text-transform:uppercase}
    .note{font-size:10.5px;color:#b33;margin-top:5px;text-align:center;font-style:italic}
    """
    html = f"""<!doctype html><meta charset=utf-8><title>FashionSigLIP test — visual</title><style>{css}</style>
    <div class=hd>
      <h1>FashionSigLIP QA test — sorted by match score (lowest first)</h1>
      <p>Each card: the <b>generated product shot</b> (big) + source cutout (small) · the model's match <b>score</b> · your <b>vote</b>.</p>
      <p>If the score worked, all 👎 would sit at the far left (lowest scores). Instead your 8 downvotes land at positions
      <b>{', '.join(map(str, downs))}</b> of {len(rows)} — scattered, not clustered.</p>
    </div>
    <div class=legend>Green bar = you rated 👍 up · Red bar = 👎 down. Notice the lowest-scoring cards (#1–8) are mostly green (good garments the model ranked worst), and red cards sit mid-pack. That overlap is why it was not wired in.</div>
    <div class=grid>{''.join(cards)}</div>"""
    PAGE.write_text(html, encoding="utf-8")
    print(f"wrote {PAGE} ({len(html)/1e6:.2f} MB, {len(rows)} garments)")


if __name__ == "__main__":
    main()
