"""Self-contained rating page for the OminiControl batch output.

Static HTML + vanilla JS (no server, no deps) so it opens directly from disk.
Every garment gets a thumbs up/down and a notes field; state persists in
localStorage as you go, and an Export button downloads a JSON verdict file
plus copies it to the clipboard for handing back.

Usage: python pipeline/scripts/build_rating_page.py
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "review" / "garments_omini" / "shots"
SAMPLES = ROOT / "samples"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
OUT = ROOT / "review" / "garments_omini" / "rate.html"


def _thumb(path: Path, mx: int = 420) -> str:
    im = Image.open(path)
    im.load()
    w, h = im.size
    sc = min(1.0, mx / max(w, h))
    if sc < 1.0:
        im = im.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=84, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def main() -> None:
    conf_path = SHOTS.parent / "confidence.json"
    conf = json.loads(conf_path.read_text(encoding="utf-8")) if conf_path.exists() else {}
    stems = sorted({p.name.rsplit("_", 2)[0] for p in SHOTS.glob("*.png")})
    outfits = []
    categories = set()
    for stem in stems:
        desc = DESCS / f"{stem}.json"
        garments = json.loads(desc.read_text(encoding="utf-8")) if desc.exists() else []
        src = SAMPLES / f"{stem}.jpg"
        items = []
        for p in sorted(SHOTS.glob(f"{stem}_*.png"),
                        key=lambda q: int(q.stem.rsplit("_", 2)[1])):
            i = int(p.stem.rsplit("_", 2)[1])
            g = garments[i] if i < len(garments) else {}
            cat = g.get("category", "?")
            categories.add(cat)
            c = conf.get(p.stem, {})
            items.append({
                "id": p.stem,
                "img": _thumb(p),
                "item": g.get("item", "?"),
                "archetype": g.get("archetype", ""),
                "color": g.get("color", ""),
                "category": cat,
                "conf_band": c.get("review_band", "high"),
                "conf_score": c.get("review_score", 1.0),
                "conf_flags": [f for f in c.get("flags", []) if "no automatic" not in f],
            })
        outfits.append({
            "stem": stem,
            "src": _thumb(src, 320) if src.exists() else "",
            "items": items,
        })

    data_json = json.dumps(outfits, ensure_ascii=False)
    cats_json = json.dumps(sorted(categories))

    html = f"""<!doctype html><meta charset=utf-8>
<title>Rate the garment batch</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f4f3f2;color:#1c1714;font-family:Helvetica Neue,Arial,sans-serif}}
.bar{{position:sticky;top:0;z-index:10;background:#1c1714;color:#fff;padding:12px 24px;
display:flex;align-items:center;gap:16px;flex-wrap:wrap;font-size:13px}}
.bar h1{{font-size:15px;margin:0;font-weight:800;margin-right:auto}}
.bar select,.bar button{{font-size:12.5px;padding:6px 12px;border-radius:8px;border:none;
background:#332b26;color:#fff;cursor:pointer}}
.bar button.primary{{background:#cf5c7e}}
.stat{{opacity:.85}}
.stat b{{color:#fff}}
.wrap{{max-width:1100px;margin:0 auto;padding:20px 20px 80px}}
.samp{{background:#fff;border-radius:16px;padding:18px;margin-bottom:16px;
box-shadow:0 14px 34px -24px rgba(80,40,50,.5);display:grid;grid-template-columns:140px 1fr;gap:18px}}
.samp .src{{width:100%;border-radius:12px}}
.stemtag{{font-size:11px;color:#8a807b;margin-bottom:8px;font-weight:700}}
.pairs{{display:flex;flex-wrap:wrap;gap:14px}}
.card{{width:160px;border:2px solid #eee;border-radius:12px;padding:8px;transition:border-color .15s}}
.card.up{{border-color:#3f9d6d;background:#f3fbf6}}
.card.down{{border-color:#cf5c5c;background:#fdf4f4}}
.card img{{width:100%;height:150px;object-fit:contain;border-radius:8px;background:#fafafa}}
.card .lbl{{font-size:11px;color:#4a423e;margin-top:6px;line-height:1.35}}
.card .lbl b{{display:block;font-size:11.5px}}
.card .cat{{font-size:9.5px;color:#b9b0ab;text-transform:uppercase;letter-spacing:.03em}}
.votes{{display:flex;gap:6px;margin-top:7px}}
.votes button{{flex:1;padding:5px 0;border-radius:7px;border:1px solid #e2dad6;background:#fff;
cursor:pointer;font-size:14px;line-height:1}}
.votes button.active-up{{background:#3f9d6d;border-color:#3f9d6d;color:#fff}}
.votes button.active-down{{background:#cf5c5c;border-color:#cf5c5c;color:#fff}}
.note{{width:100%;margin-top:6px;font-size:11px;padding:5px 7px;border-radius:6px;
border:1px solid #e2dad6;font-family:inherit;resize:vertical;min-height:30px}}
.conf{{display:inline-block;font-size:9px;font-weight:700;padding:2px 6px;border-radius:20px;
margin-top:5px;letter-spacing:.02em}}
.conf.high{{background:#e3f4ea;color:#2c7a52}}
.conf.medium{{background:#fdf3e0;color:#9a6a1e}}
.conf.low{{background:#fbe4e4;color:#b33}}
.flag{{font-size:9.5px;color:#b33;margin-top:4px;line-height:1.3}}
.card.flagged{{border-color:#e8a33d;box-shadow:0 0 0 2px #fbe9cf}}
.hidden{{display:none !important}}
.toast{{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#1c1714;
color:#fff;padding:10px 18px;border-radius:10px;font-size:13px;opacity:0;transition:opacity .2s;
pointer-events:none}}
.toast.show{{opacity:1}}
</style>
<div class=bar>
  <h1>Rate the garment batch</h1>
  <span class=stat>Reviewed <b id=statReviewed>0</b>/<b id=statTotal>0</b></span>
  <span class=stat>👍 <b id=statUp>0</b></span>
  <span class=stat>👎 <b id=statDown>0</b></span>
  <select id=catFilter><option value="">All categories</option></select>
  <select id=viewFilter>
    <option value="all">Show all</option>
    <option value="flagged">⚠ Flagged by AI only</option>
    <option value="down">Show 👎 only</option>
    <option value="unrated">Show unrated only</option>
  </select>
  <select id=sortFilter>
    <option value="outfit">Group by outfit</option>
    <option value="conf">Lowest confidence first</option>
  </select>
  <span class=stat>⚠ <b id=statFlag>0</b> flagged</span>
  <button id=exportBtn class=primary>Export results</button>
  <button id=resetBtn>Reset</button>
</div>
<div class=wrap id=wrap></div>
<div class=toast id=toast></div>
<script>
const OUTFITS = {data_json};
const CATS = {cats_json};
const KEY = "lovanya_garment_ratings_v1";
let state = JSON.parse(localStorage.getItem(KEY) || "{{}}");

function save() {{ localStorage.setItem(KEY, JSON.stringify(state)); }}

function cardHTML(it, outfit) {{
  const st = state[it.id] || {{}};
  const flagged = (it.conf_flags && it.conf_flags.length) || it.conf_band === 'low';
  let cls = 'card';
  if (st.rating) cls += ' ' + st.rating;
  if (flagged) cls += ' flagged';
  const flagHtml = (it.conf_flags && it.conf_flags.length)
    ? `<div class=flag>⚠ ${{it.conf_flags.join('<br>⚠ ')}}</div>` : '';
  const color = it.color ? ' · ' + it.color.replace(/\\s*\\(?~?#?[0-9a-fA-F]{{6}}\\)?/,'') : '';
  return `
    <div class="${{cls}}" data-id="${{it.id}}">
      <img src="${{it.img}}">
      <div class=lbl><span class=cat>${{it.category}} · ${{outfit.stem}}</span>
        <b>${{it.archetype || it.item}}</b>${{color}}
      </div>
      <span class="conf ${{it.conf_band}}">AI ${{it.conf_band}} ${{Math.round(it.conf_score*100)}}%</span>
      ${{flagHtml}}
      <div class=votes>
        <button data-v="up" class="${{st.rating==='up'?'active-up':''}}">👍</button>
        <button data-v="down" class="${{st.rating==='down'?'active-down':''}}">👎</button>
      </div>
      <textarea class=note placeholder="what's wrong / correct type...">${{st.note||''}}</textarea>
    </div>`;
}}

function passesFilter(it, catF, viewF) {{
  const st = state[it.id] || {{}};
  const flagged = (it.conf_flags && it.conf_flags.length) || it.conf_band === 'low';
  if (catF && it.category !== catF) return false;
  if (viewF === 'down' && st.rating !== 'down') return false;
  if (viewF === 'unrated' && st.rating) return false;
  if (viewF === 'flagged' && !flagged) return false;
  return true;
}}

function render() {{
  const catF = document.getElementById('catFilter').value;
  const viewF = document.getElementById('viewFilter').value;
  const sortF = document.getElementById('sortFilter').value;
  const wrap = document.getElementById('wrap');
  wrap.innerHTML = '';
  let total = 0, reviewed = 0, up = 0, down = 0, flag = 0;

  // global stats (all items, unfiltered)
  for (const outfit of OUTFITS) for (const it of outfit.items) {{
    total++;
    const st = state[it.id] || {{}};
    if (st.rating === 'up') {{ up++; reviewed++; }}
    else if (st.rating === 'down') {{ down++; reviewed++; }}
    if ((it.conf_flags && it.conf_flags.length) || it.conf_band === 'low') flag++;
  }}

  if (sortF === 'conf') {{
    // flat list, lowest confidence (and flagged) first
    const all = [];
    for (const outfit of OUTFITS) for (const it of outfit.items)
      if (passesFilter(it, catF, viewF)) all.push({{it, outfit}});
    all.sort((a, b) => a.it.conf_score - b.it.conf_score);
    const cards = all.map(x => cardHTML(x.it, x.outfit)).join('');
    if (cards) wrap.insertAdjacentHTML('beforeend',
      `<section class=samp style="grid-template-columns:1fr"><div class=pairs>${{cards}}</div></section>`);
  }} else {{
    for (const outfit of OUTFITS) {{
      const cards = outfit.items.filter(it => passesFilter(it, catF, viewF))
        .map(it => cardHTML(it, outfit)).join('');
      if (!cards) continue;
      wrap.insertAdjacentHTML('beforeend', `
        <section class=samp>
          <div><div class=stemtag>${{outfit.stem}}</div><img class=src src="${{outfit.src}}"></div>
          <div class=pairs>${{cards}}</div>
        </section>`);
    }}
  }}

  document.getElementById('statTotal').textContent = total;
  document.getElementById('statReviewed').textContent = reviewed;
  document.getElementById('statUp').textContent = up;
  document.getElementById('statDown').textContent = down;
  document.getElementById('statFlag').textContent = flag;
}}

document.getElementById('wrap').addEventListener('click', e => {{
  const btn = e.target.closest('button[data-v]');
  if (!btn) return;
  const card = btn.closest('.card');
  const id = card.dataset.id;
  const v = btn.dataset.v;
  const cur = state[id] || {{}};
  cur.rating = (cur.rating === v) ? null : v;
  state[id] = cur;
  save();
  render();
}});
document.getElementById('wrap').addEventListener('change', e => {{
  if (!e.target.classList.contains('note')) return;
  const card = e.target.closest('.card');
  const id = card.dataset.id;
  const cur = state[id] || {{}};
  cur.note = e.target.value;
  state[id] = cur;
  save();
}});

function toast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 1800);
}}

document.getElementById('exportBtn').onclick = () => {{
  const rows = [];
  for (const outfit of OUTFITS) for (const it of outfit.items) {{
    const st = state[it.id];
    if (!st || !st.rating) continue;
    rows.push({{stem: outfit.stem, id: it.id, category: it.category,
      item: it.item, archetype: it.archetype, color: it.color,
      rating: st.rating, note: st.note || '',
      ai_conf_band: it.conf_band, ai_conf_score: it.conf_score,
      ai_flags: it.conf_flags || []}});
  }}
  const payload = {{exported_at: new Date().toISOString(),
    total: rows.length, up: rows.filter(r=>r.rating==='up').length,
    down: rows.filter(r=>r.rating==='down').length, results: rows}};
  const text = JSON.stringify(payload, null, 2);
  const blob = new Blob([text], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'garment-ratings.json';
  a.click();
  navigator.clipboard && navigator.clipboard.writeText(text).catch(()=>{{}});
  toast('Downloaded garment-ratings.json (also copied to clipboard)');
}};

document.getElementById('resetBtn').onclick = () => {{
  if (!confirm('Clear all ratings and notes?')) return;
  state = {{}}; save(); render();
}};
document.getElementById('catFilter').onchange = render;
document.getElementById('viewFilter').onchange = render;
document.getElementById('sortFilter').onchange = render;

for (const c of CATS) {{
  const o = document.createElement('option'); o.value = c; o.textContent = c;
  document.getElementById('catFilter').appendChild(o);
}}
render();
</script>"""

    OUT.write_text(html, encoding="utf-8")
    n = sum(len(o["items"]) for o in outfits)
    print(f"wrote {OUT}  ({len(html)/1e6:.2f} MB, {n} garments, {len(outfits)} outfits)")


if __name__ == "__main__":
    main()
