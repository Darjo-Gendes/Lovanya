"""Render Lovänya Style Snapshot cards to a standalone HTML file.

The "style card" is a React component (lovanya/components/LookCard.tsx) driven by
lovanya/lib/lookcard.ts. This ports both — the deterministic buildLookCard logic
AND the card design (tokens, fonts, the 4 layouts) — to plain HTML/CSS, embeds
the garment images as base64, and writes ONE self-contained file that opens in
any browser (or drops on Cloudflare Pages). No React, no build step.

Reads the same look-file interchange as the app, so it renders the fixture today
and the garment-extraction output (review/extract/looks.json) later.

Usage (from repo root):
    python pipeline/scripts/build_lookcards_html.py
    python pipeline/scripts/build_lookcards_html.py pipeline/review/extract/looks.json
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
LOVANYA = REPO / "lovanya"
PUBLIC = LOVANYA / "public"
sys.path.insert(0, str(REPO))
from pipeline.app.color import color_name  # noqa: E402  (mirrors lib/color.ts colorName)

DEFAULT_JSON = PUBLIC / "fixtures" / "looks.json"
DEFAULT_OUT = REPO / "pipeline" / "review" / "lookcards" / "index.html"

# --- lib/lookcard.ts constants ------------------------------------------------
CATEGORY_WEIGHT = {"outerwear": 1.0, "dress": 0.92, "top": 0.8, "bottom": 0.68,
                   "shoes": 0.55, "bag": 0.45, "accessory": 0.35}
DEFAULT_AT = 1767225600000  # Date.UTC(2026,0,1,12) in ms, matches garment-json.ts
HEX = "#0123456789abcdefABCDEF"


# --- lib/color.ts shade() -----------------------------------------------------
def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def shade(hexs: str, amt: float) -> str:
    r, g, b = _hex_to_rgb(hexs)
    def f(v):
        return v + (255 - v) * (amt / 100) if amt >= 0 else v * (1 + amt / 100)
    return "#%02x%02x%02x" % (round(f(r)), round(f(g)), round(f(b)))


# --- garment-json.ts: JSON garment -> app item --------------------------------
def _read_colors(g: dict) -> list[str]:
    out = []
    def push(c):
        if isinstance(c, str) and len(c) == 7 and c[0] == "#" and all(ch in HEX for ch in c[1:]) and c not in out:
            out.append(c)
    for c in (g.get("colors") or []):
        push(c)
    push(g.get("color_primary"))
    push(g.get("color_secondary"))
    return out


def parse_lookfile(data: dict):
    garments = {}
    for i, g in enumerate(data.get("garments", [])):
        if not isinstance(g, dict):
            continue
        colors = _read_colors(g)
        if not g.get("category") or not colors:
            continue
        gid = g.get("id") or f"json-{i}"
        garments[gid] = {
            "id": gid, "category": g["category"], "colors": colors,
            "photo": g.get("cutout_url") or g.get("image_url"),
            "loved": g.get("loved") is True,
            "addedAt": g.get("added_at", DEFAULT_AT),
            "clarity": g.get("clarity"), "dominance": g.get("dominance"),
        }
    outfits = []
    for i, o in enumerate(data.get("outfits", [])):
        ids = [gid for gid in o.get("garment_ids", []) if gid in garments]
        if not ids:
            continue
        outfits.append({"id": o.get("id") or f"outfit-{i}",
                        "garments": [garments[g] for g in ids],
                        "occasion": o.get("occasion"),
                        "createdAt": o.get("created_at", DEFAULT_AT)})
    if not outfits:  # garments-only file: one solo look each
        for g in garments.values():
            outfits.append({"id": f"solo-{g['id']}", "garments": [g],
                            "occasion": None, "createdAt": g["addedAt"]})
    return outfits


# --- lib/lookcard.ts: buildLookCard() -----------------------------------------
def _layout(n: int) -> str:
    return "center" if n <= 1 else "diagonal" if n == 2 else "stack" if n <= 4 else "grid"


def _clarity_proxy(item) -> float:
    return 0.9 if item.get("photo") else 0.35


def _hero_score(item, recency) -> float:
    clarity = item["clarity"] if item.get("clarity") is not None else _clarity_proxy(item)
    category = CATEGORY_WEIGHT.get(item["category"], 0.5)
    dominance = item["dominance"] if item.get("dominance") is not None else category
    favorite = 1 if item.get("loved") else 0
    return clarity * 0.35 + category * 0.25 + dominance * 0.2 + recency * 0.1 + favorite * 0.1


def _recency(garments) -> dict:
    ordered = sorted(garments, key=lambda g: g["addedAt"])  # stable
    span = max(len(ordered) - 1, 1)
    return {g["id"]: (1.0 if len(garments) == 1 else i / span) for i, g in enumerate(ordered)}


def _fmt_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%b %-d, %Y") \
        if sys.platform != "win32" else datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%b %#d, %Y")


def build_card(outfit):
    garments = outfit["garments"]
    ranks = _recency(garments)
    scored = sorted(garments, key=lambda g: (-_hero_score(g, ranks.get(g["id"], 0)), g["id"]))
    hero = scored[0]
    palette = []
    for g in scored:
        for c in g["colors"]:
            if c and c not in palette:
                palette.append(c)
            if len(palette) >= 4:
                break
        if len(palette) >= 4:
            break
    if not palette:
        palette = ["#d8c4bc"]
    names = [color_name(c) for c in palette[:2]]
    if len(names) > 1 and names[0] != names[1]:
        title = f"{names[0].capitalize()} & {names[1]}"
    else:
        title = names[0].capitalize()
    occ = outfit["occasion"]
    subtitle = f"{_fmt_date(outfit['createdAt'])} · {occ.capitalize()}" if occ else _fmt_date(outfit["createdAt"])
    hn = color_name(hero["colors"][0] if hero["colors"] else "#d8c4bc")
    caption = (f"Your {hn} {hero['category']} takes the spotlight." if len(garments) == 1
               else f"{hn.capitalize()} {hero['category']} anchors a {len(garments)}-piece look.")
    return {"title": title, "subtitle": subtitle, "caption": caption,
            "layout": _layout(len(garments)), "hero": hero, "rest": [g for g in scored if g is not hero],
            "palette": palette}


# --- image embedding ----------------------------------------------------------
def resolve_image(url: str | None, json_dir: Path) -> str | None:
    if not url:
        return None
    p = (PUBLIC / url.lstrip("/")) if url.startswith("/") else (json_dir / url)
    if not p.exists():
        return None
    mime = "png" if p.suffix.lower() == ".png" else "jpeg"
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()


# --- HTML rendering (mirrors LookCard.tsx) ------------------------------------
def thumb(item, img_by_id, style="", rounded=18, cover_box=True):
    data = img_by_id.get(item["id"])
    c0 = item["colors"][0] if item["colors"] else "#d8c4bc"
    inner = (f'<img src="{data}" style="width:100%;height:100%;object-fit:cover;display:block">'
             if data else
             f'<div style="display:flex;height:100%;width:100%;align-items:center;justify-content:center">'
             f'<span style="height:38px;width:38px;border-radius:50%;background:{c0}"></span></div>')
    bg = "" if data else f"background:linear-gradient(160deg,{shade(c0,86)},{shade(c0,62)});"
    ar = "aspect-ratio:1;" if cover_box else "height:100%;width:100%;"
    return (f'<div style="position:absolute;overflow:hidden;border-radius:{rounded}px;{ar}{bg}'
            f'box-shadow:0 10px 22px -14px rgba(120,80,90,.5);{style}">{inner}</div>')


def visual(card, img_by_id) -> str:
    hero, rest, layout = card["hero"], card["rest"], card["layout"]
    p = card["palette"]
    bg = f"linear-gradient(150deg,{shade(p[0], 88)},{shade(p[1] if len(p) > 1 else p[0], 68)})"
    inner = ""
    if layout == "center":
        inner = thumb(hero, img_by_id, "left:50%;top:50%;width:56%;transform:translate(-50%,-50%);", 16)
    elif layout == "diagonal":
        inner = thumb(hero, img_by_id, "left:6%;top:6%;width:54%;transform:rotate(-2deg);", 16)
        if rest:
            inner += thumb(rest[0], img_by_id, "bottom:6%;right:6%;width:42%;transform:rotate(2deg);", 16)
    elif layout == "stack":
        inner = thumb(hero, img_by_id, "left:5%;top:50%;width:52%;transform:translateY(-50%);", 16)
        for i, g in enumerate(rest[:3]):
            inner += thumb(g, img_by_id, f"right:5%;top:{8 + i * 30}%;width:34%;", 12)
    else:  # grid — hero spans 2x2 in a 3x3
        cells = [f'<div style="grid-column:span 2;grid-row:span 2;position:relative;border-radius:12px;overflow:hidden">'
                 + thumb(hero, img_by_id, "inset:0;width:100%;height:100%;", 12, cover_box=False) + '</div>']
        for g in rest[:5]:
            cells.append('<div style="position:relative;border-radius:12px;overflow:hidden">'
                         + thumb(g, img_by_id, "inset:0;width:100%;height:100%;", 12, cover_box=False) + '</div>')
        return (f'<div class="visual" style="background:{bg}"><div style="display:grid;height:100%;'
                f'grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(3,1fr);gap:6px;padding:6px">'
                + "".join(cells) + '</div></div>')
    return f'<div class="visual" style="background:{bg}">{inner}</div>'


def card_html(card, img_by_id) -> str:
    swatches = "".join(f'<span class="sw" style="background:{c}"></span>' for c in card["palette"][:4])
    return f"""<div class="card">
  <div class="head"><span class="logo">Lovänya</span><span class="eyebrow">Style Snapshot</span></div>
  <h3 class="title">{card['title']}</h3><p class="sub">{card['subtitle']}</p>
  {visual(card, img_by_id)}
  <div class="foot"><div class="sws">{swatches}</div><p class="cap">{card['caption']}</p></div>
</div>"""


PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lovänya — Style Cards</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" media="print" onload="this.media='all'"
 href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=Poppins:wght@400;500;600&family=Parisienne&display=swap">
<style>
 :root{--card:#fff;--ink:#48292e;--ink-soft:#6e5a5a;--ink-faint:#a2908f;--rosewood:#d56f88;--line:#efdbdd;--bg:#e8dada}
 *{box-sizing:border-box}body{margin:0;background:var(--bg);font-family:'Poppins',system-ui,Segoe UI,sans-serif;color:var(--ink-soft)}
 .wrap{max-width:900px;margin:0 auto;padding:26px 18px 70px}
 h1.page{font-family:'Playfair Display',Georgia,serif;color:var(--ink);font-size:26px;margin:0 0 2px}
 .lede{font-size:13px;margin:0 0 18px}
 .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:22px}
 .card{background:var(--card);border:1px solid var(--line);border-radius:26px;overflow:hidden;
   box-shadow:0 18px 40px -22px rgba(206,140,150,.55)}
 .head{display:flex;align-items:center;justify-content:space-between;padding:16px 20px 0}
 .logo{font-family:'Parisienne',cursive;font-size:22px;color:var(--rosewood);line-height:1}
 .eyebrow{font-size:9px;font-weight:600;letter-spacing:1.4px;text-transform:uppercase;color:var(--ink-faint)}
 .title{font-family:'Playfair Display',serif;font-weight:600;font-size:18px;color:var(--ink);margin:4px 20px 0}
 .sub{font-size:11px;color:var(--ink-faint);margin:2px 20px 0}
 .visual{position:relative;margin:14px 20px 0;aspect-ratio:4/3.4;border-radius:18px;overflow:hidden}
 .foot{display:flex;align-items:center;gap:8px;padding:12px 20px 16px}
 .sws{display:flex;gap:4px}.sw{width:14px;height:14px;border-radius:50%;border:1px solid var(--line);display:inline-block}
 .cap{flex:1;min-width:0;text-align:right;font-size:11px;color:var(--ink-soft);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin:0}
</style></head><body><div class="wrap">
 <h1 class="page">Style Snapshot cards</h1>
 <p class="lede">Standalone HTML of <b>LookCard.tsx</b> — rendered from __SRC__ · __N__ looks. Same deterministic layout the app uses.</p>
 <div class="cards">__CARDS__</div>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("json", nargs="?", default=str(DEFAULT_JSON), help="look-file (default: app fixture)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    json_path = Path(args.json).resolve()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    outfits = parse_lookfile(data)

    img_by_id = {}
    for o in outfits:
        for g in o["garments"]:
            if g["id"] not in img_by_id:
                img_by_id[g["id"]] = resolve_image(g.get("photo"), json_path.parent)

    cards = [card_html(build_card(o), img_by_id) for o in outfits]
    html = (PAGE.replace("__CARDS__", "\n".join(cards))
                .replace("__N__", str(len(cards)))
                .replace("__SRC__", json_path.name))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    embedded = sum(1 for v in img_by_id.values() if v)
    print(f"Wrote {out}  ({len(cards)} cards, {embedded}/{len(img_by_id)} garment images embedded)")


if __name__ == "__main__":
    main()
