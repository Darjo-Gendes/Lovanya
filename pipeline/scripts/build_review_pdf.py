"""Render the outfit review to PDF: one outfit per page — photo + Claude
verdict + Qwen 8B verdict only — split 30 outfits per file.

Reuses the data loaders from build_review.py (same gold + 8B sources, same
mojibake fix), so the PDFs stay consistent with the HTML page and JSONL.
Deduplicated to the 120 unique sample photos, so it's exactly 4 PDFs of 30.

Usage (from repo root or pipeline/):
    python pipeline/scripts/build_review_pdf.py
    -> writes pipeline/review/pdf/lovanya-review-partNof4.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import build_review as br  # noqa: E402  (shared loaders: load_gold, parse_8b, ...)

OUTDIR = br.PIPELINE / "review" / "pdf"
CHUNK = 30
SK = br.SCORE_KEYS
SLABEL = {"color_harmony": "Harmony", "occasion_fit": "Occasion",
          "silhouette_balance": "Silhouette", "cohesion": "Cohesion"}
CLAUDE = "#B08948"
QWEN = "#7C6BB0"

# --- fonts: Arial covers the em-dashes, ä in "Lovänya", and curly quotes ------
try:
    pdfmetrics.registerFont(TTFont("App", "C:/Windows/Fonts/arial.ttf"))
    pdfmetrics.registerFont(TTFont("App-Bold", "C:/Windows/Fonts/arialbd.ttf"))
    pdfmetrics.registerFontFamily("App", normal="App", bold="App-Bold")
    FONT, FONT_B = "App", "App-Bold"
except Exception:
    FONT, FONT_B = "Helvetica", "Helvetica-Bold"

H = ParagraphStyle("h", fontName=FONT_B, fontSize=13, leading=16,
                   textColor=HexColor("#48292E"), spaceAfter=2)
BODY = ParagraphStyle("body", fontName=FONT, fontSize=9.5, leading=13,
                      textColor=HexColor("#3E2A2E"), spaceAfter=2)
SMALL = ParagraphStyle("small", fontName=FONT, fontSize=8.5, leading=11,
                       textColor=HexColor("#8A7674"), spaceAfter=3)
SLOT = ParagraphStyle("slot", fontName=FONT, fontSize=9.5, leading=13,
                      textColor=HexColor("#B9A7A6"))


def esc(s) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def build_entries() -> list[dict]:
    gold = br.load_gold()
    q8b = br.parse_8b(br.EVAL_8B.read_text(encoding="utf-8")) if br.EVAL_8B.exists() else []
    by_key = {(r["image"], r["occasion"]): r for r in q8b}
    by_img: dict[str, dict] = {}
    for r in q8b:
        by_img.setdefault(r["image"], r)

    entries = []
    for g in gold:
        base = Path(g["image"]).name
        occ = g.get("occasion", "")
        eight = by_key.get((base, occ)) or by_img.get(base)
        entries.append({
            "base": base,
            "path": br.SAMPLES / base,
            "occasion": occ,
            "gold": {k: g.get(k) for k in ("scores", "overall", "feedback", "one_fix")},
            "q8b": eight,
        })
    # Outfits Qwen actually judged float to the front (they're the comparisons).
    entries.sort(key=lambda e: (e["q8b"] is None, e["base"]))
    return entries


def scaled_image(path: Path, max_w: float, max_h: float):
    try:
        iw, ih = ImageReader(str(path)).getSize()
    except Exception:
        return None
    scale = min(max_w / iw, max_h / ih)
    return Image(str(path), width=iw * scale, height=ih * scale)


def verdict_flowables(title: str, v: dict, color: str) -> list:
    scores = v.get("scores") or {}
    sc = " &nbsp;·&nbsp; ".join(f"{SLABEL[k]} {scores.get(k, '–')}" for k in SK)
    out = [Paragraph(f'<font color="{color}"><b>{title} — {v.get("overall", "–")}/10</b></font>', BODY),
           Paragraph(sc, SMALL)]
    if v.get("feedback"):
        out.append(Paragraph(esc(v["feedback"]), BODY))
    if v.get("one_fix"):
        out.append(Paragraph(f"<b>Fix:</b> {esc(v['one_fix'])}", BODY))
    return out


def entry_flowables(e: dict) -> list:
    fl = [Paragraph(f"{esc(cap(e['occasion']))} &nbsp;·&nbsp; {esc(e['base'])}", H), Spacer(1, 6)]
    img = scaled_image(e["path"], 2.6 * inch, 3.1 * inch)
    if img:
        fl.append(img)
    fl.append(Spacer(1, 10))
    fl += verdict_flowables("Claude gold", e["gold"], CLAUDE)
    fl.append(Spacer(1, 8))
    if e["q8b"]:
        note = ""
        if e["q8b"]["occasion"] != e["occasion"]:
            note = f" (judged for: {e['q8b']['occasion']})"
        fl += verdict_flowables("Qwen 8B" + note, e["q8b"], QWEN)
    else:
        fl.append(Paragraph("<b>Qwen 8B</b> — not run yet "
                            "(generate on the RTX 4060 Ti, then re-run this script)", SLOT))
    return fl


def footer(part: int, total: int):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(HexColor("#A2908F"))
        canvas.drawString(0.75 * inch, 0.45 * inch,
                          f"Lovänya · Claude vs Qwen 8B · part {part}/{total}")
        canvas.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"page {doc.page}")
        canvas.restoreState()
    return draw


def build_pdf(chunk: list[dict], out_path: Path, part: int, total: int):
    doc = SimpleDocTemplate(
        str(out_path), pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title=f"Lovänya outfit review — part {part} of {total}",
        author="Lovänya review builder",
    )
    story = []
    for i, e in enumerate(chunk):
        story += entry_flowables(e)
        if i < len(chunk) - 1:
            story.append(PageBreak())
    draw = footer(part, total)
    doc.build(story, onFirstPage=draw, onLaterPages=draw)


def main():
    entries = build_entries()
    chunks = [entries[i:i + CHUNK] for i in range(0, len(entries), CHUNK)]
    total = len(chunks)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    n_8b = sum(1 for e in entries if e["q8b"])
    for idx, ch in enumerate(chunks, 1):
        out = OUTDIR / f"lovanya-review-part{idx}of{total}.pdf"
        build_pdf(ch, out, idx, total)
        print(f"Wrote {out}  ({len(ch)} outfits)")
    print(f"\n{len(entries)} unique photos · {n_8b} with a Qwen-8B verdict "
          f"(front-loaded into part 1) · {total} PDFs")


if __name__ == "__main__":
    main()
