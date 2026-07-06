"""Assemble the standalone Judgment Review page (no GPU, no server).

Reads what already exists on disk and bakes it into ONE self-contained HTML
file you can open directly or drop on Cloudflare Pages:

  data/gold.jsonl          -> Claude "gold" verdicts (the answer key, 120)
  EVAL-REPORT-8b-base.md   -> Qwen3-VL-8B verdicts (7 photos, parsed from md)
  samples/*.jpg            -> the outfit photos (embedded as base64)
  data/ratings.jsonl       -> your saved human verdicts, if any (to pre-load)

The 3B and fine-tuned columns are intentionally left as empty, labelled slots
— run those on the RTX 4060 Ti later and re-run this script to fill them in.

Usage (from repo root or pipeline/):
    python pipeline/scripts/build_review.py
    -> writes pipeline/review/index.html
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent.parent
GOLD = PIPELINE / "data" / "gold.jsonl"
EVAL_8B = PIPELINE / "EVAL-REPORT-8b-base.md"
RATINGS = PIPELINE / "data" / "ratings.jsonl"
SAMPLES = PIPELINE / "samples"
OUT = PIPELINE / "review" / "index.html"
OUT_JSONL = PIPELINE / "review" / "review.jsonl"

SCORE_KEYS = ["color_harmony", "occasion_fit", "silhouette_balance", "cohesion"]


def demojibake(s: str) -> str:
    """gold.jsonl stored UTF-8 em-dashes that were decoded as cp1252 (â€"),
    then JSON-escaped. Recover the real characters; leave clean text alone."""
    if not isinstance(s, str) or not any(c in s for c in "â€"):
        return s
    for enc in ("cp1252", "latin-1"):
        try:
            fixed = s.encode(enc).decode("utf-8")
            if fixed != s:
                return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s


def clean(obj):
    if isinstance(obj, str):
        return demojibake(obj)
    if isinstance(obj, list):
        return [clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    return obj


def load_gold() -> list[dict]:
    rows = []
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(clean(json.loads(line)))
    return rows


def parse_8b(md_text: str) -> list[dict]:
    """Parse the markdown eval report into structured verdicts."""
    out = []
    # Split on the per-sample headings.
    blocks = re.split(r"\n## ", "\n" + md_text)
    for b in blocks:
        m = re.match(r"(sample_r\dc\d)\.jpg\s+—\s+(.+?)\s+\((\d+)s\)", b)
        if not m:
            continue
        image, occasion, seconds = m.group(1) + ".jpg", m.group(2).strip(), int(m.group(3))
        items = re.search(r"\*\*Perception:\*\*\s*(\[.*?\])\s*·\s*modest:\s*(\w+)", b, re.S)
        scores = re.search(r"\*\*Scores:\*\*\s*(\{.*?\})\s*·\s*overall\s*(\d+)", b, re.S)
        feedback = re.search(r"\n>\s*(.+?)\n\n", b, re.S)
        one_fix = re.search(r"\*\*One fix:\*\*\s*(.+?)\s*(?:\n##|\Z)", b, re.S)
        try:
            perc_items = json.loads(items.group(1)) if items else []
        except json.JSONDecodeError:
            perc_items = []
        out.append({
            "image": image,
            "occasion": occasion,
            "seconds": seconds,
            "items": clean(perc_items),
            "modest": (items.group(2).lower() == "true") if items else None,
            "scores": json.loads(scores.group(1)) if scores else {},
            "overall": int(scores.group(2)) if scores else None,
            "feedback": clean(feedback.group(1).strip()) if feedback else "",
            "one_fix": clean(one_fix.group(1).strip()) if one_fix else "",
        })
    return out


def load_ratings() -> dict:
    if not RATINGS.exists():
        return {}
    by_id = {}
    for line in RATINGS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rid = f"{Path(r.get('image','')).stem}__{r.get('occasion','')}"
        by_id[rid] = r
    return by_id


def img_data_uri(basename: str) -> str | None:
    p = SAMPLES / basename
    if not p.exists():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def build_entries() -> list[dict]:
    gold = load_gold()
    q8b = parse_8b(EVAL_8B.read_text(encoding="utf-8")) if EVAL_8B.exists() else []
    q8b_by_key = {(r["image"], r["occasion"]): r for r in q8b}

    entries = []
    seen_8b = set()
    img_cache: dict[str, str | None] = {}

    def get_img(basename):
        if basename not in img_cache:
            img_cache[basename] = img_data_uri(basename)
        return img_cache[basename]

    for g in gold:
        base = Path(g["image"]).name
        occ = g.get("occasion", "")
        key = (base, occ)
        eight = q8b_by_key.get(key)
        if eight:
            seen_8b.add(key)
        entries.append({
            "id": f"{Path(base).stem}__{occ}",
            "image": g["image"],
            "base": base,
            "occasion": occ,
            "img": get_img(base),
            "gold": {k: g.get(k) for k in ("scores", "overall", "feedback", "one_fix")},
            "q8b": ({k: eight.get(k) for k in
                     ("scores", "overall", "feedback", "one_fix", "items", "modest", "seconds")}
                    if eight else None),
            "q3b": None,
            "finetuned": None,
        })

    # 8B verdicts with no matching gold row (e.g. r2c6 / weekend brunch) —
    # keep them as 8B-only rows so nothing is dropped.
    for r in q8b:
        key = (r["image"], r["occasion"])
        if key in seen_8b:
            continue
        entries.append({
            "id": f"{Path(r['image']).stem}__{r['occasion']}",
            "image": f"samples/{r['image']}",
            "base": r["image"],
            "occasion": r["occasion"],
            "img": get_img(r["image"]),
            "gold": None,
            "q8b": {k: r.get(k) for k in
                    ("scores", "overall", "feedback", "one_fix", "items", "modest", "seconds")},
            "q3b": None,
            "finetuned": None,
        })

    # Rows that have an 8B verdict are the interesting ones — float them up.
    entries.sort(key=lambda e: (e["q8b"] is None, e["base"], e["occasion"]))
    return entries


def write_review_jsonl(entries) -> None:
    """Image-free, one-outfit-per-line dump for pasting into a chat model.

    Same verdict data as the page, minus the base64 photos — id, occasion,
    each source's verdict, and the (currently empty) 3B / fine-tuned slots.
    """
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for e in entries:
            rec = {
                "id": e["id"],
                "image": e["image"],
                "occasion": e["occasion"],
                "gold": e["gold"],
                "q8b": e["q8b"],
                "q3b": e["q3b"],
                "finetuned": e["finetuned"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    entries = build_entries()
    ratings = load_ratings()
    n_8b = sum(1 for e in entries if e["q8b"])
    n_gold = sum(1 for e in entries if e["gold"])

    data_json = json.dumps(
        {"entries": entries, "preloaded_ratings": ratings, "score_keys": SCORE_KEYS},
        ensure_ascii=False,
    ).replace("</", "<\\/")  # keep an embedded </script> from closing the tag

    html = HTML_TEMPLATE.replace("__DATA__", data_json) \
        .replace("__N_TOTAL__", str(len(entries))) \
        .replace("__N_GOLD__", str(n_gold)) \
        .replace("__N_8B__", str(n_8b))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    write_review_jsonl(entries)
    size_mb = OUT.stat().st_size / 1_048_576
    print(f"Wrote {OUT}  ({size_mb:.1f} MB)")
    print(f"Wrote {OUT_JSONL}  (image-free, {len(entries)} lines)")
    print(f"  entries: {len(entries)}  ·  with Claude gold: {n_gold}  ·  with Qwen-8B: {n_8b}")
    print(f"  3B / fine-tuned: 0 (empty slots — generate on the RTX 4060 Ti, then re-run)")
    if ratings:
        print(f"  pre-loaded human ratings: {len(ratings)}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lovänya — Judgment Review &amp; Taste Trainer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- non-blocking: the page paints immediately with system-font fallbacks even
     offline (Cloudflare/online just gets the pretty fonts as an upgrade). -->
<link rel="stylesheet" media="print" onload="this.media='all'"
  href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&family=Parisienne&display=swap">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&family=Parisienne&display=swap"></noscript>
<style>
  :root{
    --pink:#D56F88; --accent:#CE6E86; --accent2:#CE6C84;
    --btn:linear-gradient(135deg,#E48EA0,#CE6C84);
    --soft:linear-gradient(155deg,#F8E1E1 0%,#F3D2D7 100%);
    --screen:#FAEDED; --body-bg:#E8DADA;
    --head:#48292E; --head2:#3E2A2E; --body:#6E5A5A; --muted:#A2908F;
    --up:#4B8B5B; --down:#C05555; --slot:#B9A7A6;
    --gold:#B08948; --eight:#7C6BB0;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--body-bg);color:var(--body);
    font-family:'Poppins',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-weight:300;}
  a{color:var(--accent2)}
  .wrap{max-width:1100px;margin:0 auto;padding:24px 18px 140px;}
  .eyebrow{font-size:10px;font-weight:600;letter-spacing:1.5px;color:var(--accent);text-transform:uppercase;}
  h1{font-family:'Playfair Display',Georgia,serif;font-weight:700;color:var(--head);
    font-size:30px;margin:2px 0 2px;}
  h1 .logo{font-family:'Parisienne',cursive;font-weight:400;color:var(--accent2);}
  .lede{color:var(--body);font-size:14px;max-width:720px;}
  .panel{background:#fff;border-radius:18px;padding:16px 18px;margin:16px 0;
    box-shadow:0 12px 26px -18px rgba(206,150,150,.5);}
  .about summary{cursor:pointer;font-weight:600;color:var(--head);}
  .about p{font-size:13px;line-height:1.55;}
  .about .k{font-weight:600;color:var(--head2);}
  .stat-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;}
  .stat{background:var(--soft);border-radius:14px;padding:10px 14px;min-width:120px;}
  .stat b{display:block;font-family:'Playfair Display',serif;font-size:22px;color:var(--head);}
  .stat span{font-size:11px;color:var(--body);}
  .toolbar{position:sticky;top:0;z-index:20;background:rgba(232,218,218,.92);
    backdrop-filter:blur(8px);padding:10px 0;margin:0 0 8px;display:flex;flex-wrap:wrap;
    gap:8px;align-items:center;}
  .toolbar input[type=text]{flex:1;min-width:160px;border:1px solid #e6cccd;border-radius:20px;
    padding:8px 14px;font-family:inherit;font-size:13px;background:#fff;color:var(--head);}
  .btn{border:none;cursor:pointer;border-radius:20px;padding:8px 14px;font-family:inherit;
    font-size:13px;font-weight:600;color:#fff;background:var(--btn);
    box-shadow:0 10px 20px -12px rgba(206,108,132,.8);}
  .btn.ghost{background:#fff;color:var(--accent2);border:1px solid #eccdd2;box-shadow:none;}
  .chip{border:1px solid #e6cccd;background:#fff;color:var(--body);border-radius:16px;
    padding:6px 12px;font-size:12px;cursor:pointer;}
  .chip.on{background:var(--accent2);color:#fff;border-color:var(--accent2);}
  .card{background:#fff;border-radius:22px;padding:16px;margin:14px 0;
    box-shadow:0 18px 36px -22px rgba(206,140,150,.5);display:grid;
    grid-template-columns:180px 1fr;gap:18px;}
  @media(max-width:720px){.card{grid-template-columns:1fr}}
  .photo{border-radius:16px;overflow:hidden;background:var(--soft);align-self:start;}
  .photo img{width:100%;display:block;}
  .photo .cap{padding:8px 10px;}
  .photo .occ{font-weight:600;color:var(--head);text-transform:capitalize;font-size:14px;}
  .photo .fn{font-size:11px;color:var(--muted);}
  .verdicts{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;}
  @media(max-width:520px){.verdicts{grid-template-columns:1fr}}
  .v{border:1px solid #f0dcdc;border-radius:14px;padding:10px 12px;}
  .v h4{margin:0 0 6px;font-size:12px;font-weight:700;letter-spacing:.3px;display:flex;
    align-items:center;gap:6px;}
  .v.gold h4{color:var(--gold)} .v.eight h4{color:var(--eight)}
  .v.slot{border-style:dashed;background:#faf5f5;color:var(--slot);}
  .v.slot .msg{font-size:12px;line-height:1.5;color:var(--slot);}
  .dot{width:9px;height:9px;border-radius:50%;display:inline-block;}
  .scores{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 8px;}
  .sc{font-size:11px;background:#f6ecec;border-radius:10px;padding:3px 7px;color:var(--head2);}
  .sc b{font-weight:600;}
  .overall{font-family:'Playfair Display',serif;font-size:15px;color:var(--head);}
  .fb{font-size:12.5px;line-height:1.5;color:var(--body);margin:4px 0;}
  .fix{font-size:12px;color:var(--head2);}
  .fix .lab{color:var(--accent);font-weight:600;}
  .changelog{grid-column:1/-1;background:#fbf3f4;border-radius:14px;padding:10px 12px;
    font-size:12px;color:var(--body);}
  .changelog .lab{font-weight:600;color:var(--head2);}
  .delta{font-weight:600;padding:1px 6px;border-radius:8px;margin:0 2px;}
  .delta.pos{background:#e3f1e6;color:var(--up);} .delta.neg{background:#f6e2e2;color:var(--down);}
  .delta.zero{background:#eee6e6;color:var(--muted);}
  .human{grid-column:1/-1;border-top:1px dashed #eccdd2;padding-top:12px;margin-top:2px;}
  .human .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
  .vote{border:1px solid #e6cccd;background:#fff;border-radius:16px;padding:6px 14px;
    cursor:pointer;font-size:15px;}
  .vote.up.on{background:#e3f1e6;border-color:var(--up);} .vote.down.on{background:#f6e2e2;border-color:var(--down);}
  .editor{margin-top:10px;display:none;}
  .editor.open{display:block;}
  .editor .grid{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;}
  .editor label{font-size:11px;color:var(--muted);display:flex;flex-direction:column;gap:2px;}
  .editor input[type=number]{width:64px;border:1px solid #e6cccd;border-radius:10px;padding:5px;}
  .editor textarea,.editor .fixin{width:100%;border:1px solid #e6cccd;border-radius:12px;
    padding:8px 10px;font-family:inherit;font-size:12.5px;color:var(--head2);}
  .editor textarea{min-height:60px;resize:vertical;}
  .saved-tag{font-size:11px;color:var(--up);font-weight:600;}
  .foot{position:fixed;bottom:0;left:0;right:0;background:#fff;
    box-shadow:0 -8px 26px -14px rgba(206,150,150,.6);padding:10px 16px;z-index:30;
    display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:center;}
  .foot .prog{font-size:12px;color:var(--body);}
  .foot .prog b{color:var(--head);}
  .name{border:1px solid #e6cccd;border-radius:20px;padding:7px 12px;font-family:inherit;
    font-size:13px;background:#fff;color:var(--head);}
  .hidden{display:none!important;}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Lovänya · internal tool</div>
  <h1><span class="logo">Lovänya</span> — Judgment Review &amp; Taste Trainer</h1>
  <p class="lede">Every outfit, side by side: what <b>Claude</b> said (the answer key),
    what <b>Qwen&nbsp;8B</b> said (the model you'll ship), and where they disagree.
    Add <b>your</b> verdict on each — that's the human taste this dataset is missing.
    Export it when you're done and drop it into <code>data/ratings.jsonl</code>.</p>

  <details class="panel about">
    <summary>How this data was made (read me first)</summary>
    <p><span class="k">Claude gold (120):</span> written offline by Claude against the styling
      framework — the high-quality target the model is trying to match. It's an AI's taste,
      not yours. That's the gap you're here to fill.</p>
    <p><span class="k">Qwen 8B (7):</span> Qwen3-VL-8B, 4-bit, actually looking at the photo.
      This is the model that would run in the app. <b>It is not fine-tuned</b> — it's the stock
      model steered by the framework text. "Training" hasn't happened yet.</p>
    <p><span class="k">Qwen 3B &amp; Fine-tuned:</span> empty slots. The 3B was never run, and no
      fine-tune exists yet. Generate both on the RTX&nbsp;4060&nbsp;Ti later and re-run
      <code>build_review.py</code> — these columns fill in automatically.</p>
    <p><span class="k">Your verdicts</span> collect toward the ~300 examples needed before the
      QLoRA fine-tune. Thumbs are a fast signal; a written verdict becomes a training example
      in its own right.</p>
  </details>

  <div class="panel">
    <div class="stat-row">
      <div class="stat"><b>__N_TOTAL__</b><span>outfits in review</span></div>
      <div class="stat"><b>__N_GOLD__</b><span>Claude gold verdicts</span></div>
      <div class="stat"><b>__N_8B__</b><span>Qwen&nbsp;8B verdicts</span></div>
      <div class="stat"><b id="rated-count">0</b><span>your verdicts so far</span></div>
    </div>
  </div>

  <div class="toolbar">
    <input id="search" type="text" placeholder="Search occasion or filename…">
    <button class="chip on" data-filter="all">All</button>
    <button class="chip" data-filter="has8b">Has 8B</button>
    <button class="chip" data-filter="unrated">Not yet rated by me</button>
    <button class="chip" data-filter="rated">Rated by me</button>
  </div>

  <div id="list"></div>
</div>

<div class="foot">
  <span class="prog">Reviewer:</span>
  <input class="name" id="reviewer" type="text" placeholder="your name" size="10">
  <span class="prog">Rated <b><span id="prog-n">0</span></b> / __N_TOTAL__</span>
  <button class="btn" id="export">⬇ Export ratings.jsonl</button>
  <button class="btn ghost" id="import-btn">⬆ Import</button>
  <input id="import-file" type="file" accept=".jsonl,.json,.txt" class="hidden">
</div>

<script>
const DATA = __DATA__;
const SK = DATA.score_keys;
const SLABEL = {color_harmony:"Harmony", occasion_fit:"Occasion", silhouette_balance:"Silhouette", cohesion:"Cohesion"};
const STORE_KEY = "lovanya_review_v1";

let store = JSON.parse(localStorage.getItem(STORE_KEY) || "null") || {reviewer:"", ratings:{}};
// Seed from any ratings baked in at build time (only if we have none locally).
if(Object.keys(store.ratings).length === 0 && DATA.preloaded_ratings){
  for(const [id,r] of Object.entries(DATA.preloaded_ratings)) store.ratings[id] = r;
}
function save(){ localStorage.setItem(STORE_KEY, JSON.stringify(store)); refreshProgress(); }

const esc = s => (s==null?"":String(s)).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function scoresHtml(sc){
  if(!sc) return "";
  return `<div class="scores">` + SK.map(k=>`<span class="sc">${SLABEL[k]} <b>${sc[k]??"–"}</b></span>`).join("") + `</div>`;
}
function verdictBlock(v, cls, name, dotColor){
  if(!v) return `<div class="v slot ${cls}"><h4><span class="dot" style="background:${dotColor}"></span>${name}</h4>
    <div class="msg">Not run yet — generate on the RTX 4060 Ti, then re-run the build script.</div></div>`;
  const secs = v.seconds ? ` · ${v.seconds}s` : "";
  return `<div class="v ${cls}"><h4><span class="dot" style="background:${dotColor}"></span>${name}
    <span class="overall">${v.overall??"–"}/10</span></h4>
    ${scoresHtml(v.scores)}
    <div class="fb">${esc(v.feedback)}</div>
    <div class="fix"><span class="lab">Fix:</span> ${esc(v.one_fix)}${secs}</div></div>`;
}
function changelog(e){
  if(!(e.gold && e.q8b && e.gold.scores && e.q8b.scores)) return "";
  const parts = SK.map(k=>{
    const d = (e.q8b.scores[k]??0) - (e.gold.scores[k]??0);
    const cls = d>0?"pos":d<0?"neg":"zero";
    const sign = d>0?`+${d}`:`${d}`;
    return `${SLABEL[k]} <span class="delta ${cls}">${sign}</span>`;
  });
  const od = (e.q8b.overall??0)-(e.gold.overall??0);
  const ocls = od>0?"pos":od<0?"neg":"zero";
  return `<div class="changelog"><span class="lab">Qwen 8B vs Claude gold:</span> ${parts.join(" · ")}
    · overall <span class="delta ${ocls}">${od>0?"+"+od:od}</span></div>`;
}
function humanBlock(e){
  const r = store.ratings[e.id] || {};
  const vote = r.verdict;
  const open = false;
  return `<div class="human" data-id="${e.id}">
    <div class="row">
      <button class="vote up ${vote==='up'?'on':''}" data-vote="up">👍</button>
      <button class="vote down ${vote==='down'?'on':''}" data-vote="down">👎</button>
      <button class="chip toggle-ed">✍ Write my verdict</button>
      <button class="chip prefill" data-from="gold">↧ from Claude</button>
      ${e.q8b?`<button class="chip prefill" data-from="q8b">↧ from 8B</button>`:""}
      <span class="saved-tag ${r.feedback||r.verdict?'':'hidden'}">saved ✓</span>
    </div>
    <div class="editor ${open?'open':''}">
      <div class="grid">
        ${SK.map(k=>`<label>${SLABEL[k]}<input type="number" min="1" max="10" data-sk="${k}" value="${(r.scores&&r.scores[k])??''}"></label>`).join("")}
        <label>Overall<input type="number" min="1" max="10" data-ov value="${r.overall??''}"></label>
      </div>
      <textarea data-fb placeholder="What I'd actually say about this outfit…">${esc(r.feedback||"")}</textarea>
      <input class="fixin" data-fix placeholder="My one fix…" value="${esc(r.one_fix||"")}">
      <div class="row" style="margin-top:8px">
        <button class="btn save-v">Save my verdict</button>
      </div>
    </div>
  </div>`;
}
function cardHtml(e){
  const img = e.img ? `<img src="${e.img}" alt="">` : `<div style="padding:40px;text-align:center;color:var(--muted)">no photo</div>`;
  return `<div class="card" data-id="${e.id}" data-occ="${esc(e.occasion)}" data-fn="${esc(e.base)}" data-has8b="${e.q8b?1:0}">
    <div class="photo">${img}<div class="cap"><div class="occ">${esc(e.occasion)}</div><div class="fn">${esc(e.base)}</div></div></div>
    <div>
      <div class="verdicts">
        ${verdictBlock(e.gold,"gold","Claude gold","var(--gold)")}
        ${verdictBlock(e.q8b,"eight","Qwen 8B","var(--eight)")}
        ${verdictBlock(e.q3b,"","Qwen 3B","var(--slot)")}
        ${verdictBlock(e.finetuned,"","Fine-tuned","var(--slot)")}
      </div>
    </div>
    ${changelog(e)}
    ${humanBlock(e)}
  </div>`;
}

const list = document.getElementById("list");
list.innerHTML = DATA.entries.map(cardHtml).join("");

// ---- interactions ----
let filter = "all", q = "";
function applyFilter(){
  document.querySelectorAll(".card").forEach(c=>{
    const id=c.dataset.id, rated=!!(store.ratings[id]&&(store.ratings[id].verdict||store.ratings[id].feedback));
    let ok=true;
    if(filter==="has8b") ok = c.dataset.has8b==="1";
    else if(filter==="unrated") ok = !rated;
    else if(filter==="rated") ok = rated;
    if(ok && q){ ok = (c.dataset.occ+" "+c.dataset.fn).toLowerCase().includes(q); }
    c.classList.toggle("hidden", !ok);
  });
}
document.querySelectorAll(".chip[data-filter]").forEach(ch=>ch.onclick=()=>{
  document.querySelectorAll(".chip[data-filter]").forEach(x=>x.classList.remove("on"));
  ch.classList.add("on"); filter=ch.dataset.filter; applyFilter();
});
document.getElementById("search").oninput = ev=>{ q=ev.target.value.trim().toLowerCase(); applyFilter(); };

list.addEventListener("click", ev=>{
  const human = ev.target.closest(".human"); if(!human) return;
  const id = human.dataset.id;
  const rec = store.ratings[id] || (store.ratings[id]={image: entryById(id).image, occasion: entryById(id).occasion});
  if(ev.target.matches(".vote")){
    const v=ev.target.dataset.vote;
    rec.verdict = (rec.verdict===v)?null:v;
    human.querySelectorAll(".vote").forEach(b=>b.classList.toggle("on", b.dataset.vote===rec.verdict));
    human.querySelector(".saved-tag").classList.remove("hidden");
    stamp(rec); save();
  }
  if(ev.target.matches(".toggle-ed")) human.querySelector(".editor").classList.toggle("open");
  if(ev.target.matches(".prefill")){
    const e=entryById(id), src=e[ev.target.dataset.from];
    if(src){
      human.querySelectorAll("[data-sk]").forEach(inp=>inp.value=(src.scores&&src.scores[inp.dataset.sk])??"");
      human.querySelector("[data-ov]").value=src.overall??"";
      human.querySelector("[data-fb]").value=src.feedback||"";
      human.querySelector("[data-fix]").value=src.one_fix||"";
      human.querySelector(".editor").classList.add("open");
    }
  }
  if(ev.target.matches(".save-v")){
    rec.scores={}; human.querySelectorAll("[data-sk]").forEach(inp=>{ if(inp.value) rec.scores[inp.dataset.sk]=+inp.value; });
    const ov=human.querySelector("[data-ov]").value; rec.overall= ov?+ov:null;
    rec.feedback=human.querySelector("[data-fb]").value.trim();
    rec.one_fix=human.querySelector("[data-fix]").value.trim();
    human.querySelector(".saved-tag").classList.remove("hidden");
    stamp(rec); save();
  }
});
function entryById(id){ return DATA.entries.find(e=>e.id===id); }
function stamp(rec){ rec.source="human-"+(store.reviewer||"anon"); rec.ts=new Date().toISOString(); }

function refreshProgress(){
  const n=Object.values(store.ratings).filter(r=>r.verdict||r.feedback).length;
  document.getElementById("prog-n").textContent=n;
  document.getElementById("rated-count").textContent=n;
}
const nameInp=document.getElementById("reviewer");
nameInp.value=store.reviewer||"";
nameInp.oninput=()=>{ store.reviewer=nameInp.value.trim(); save(); };

document.getElementById("export").onclick=()=>{
  const rows=Object.values(store.ratings).filter(r=>r.verdict||r.feedback)
    .map(r=>JSON.stringify(r));
  const blob=new Blob([rows.join("\n")+"\n"],{type:"application/x-ndjson"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob);
  a.download="ratings.jsonl"; a.click();
};
document.getElementById("import-btn").onclick=()=>document.getElementById("import-file").click();
document.getElementById("import-file").onchange=ev=>{
  const f=ev.target.files[0]; if(!f) return;
  const rd=new FileReader();
  rd.onload=()=>{
    f.text; rd.result.split(/\r?\n/).forEach(line=>{
      line=line.trim(); if(!line) return;
      try{ const r=JSON.parse(line);
        const id=(r.image||"").split("/").pop().replace(/\.[a-z]+$/i,"")+"__"+(r.occasion||"");
        store.ratings[id]=r;
      }catch(e){}
    });
    save(); location.reload();
  };
  rd.readAsText(f);
};

refreshProgress();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
