"""Marqo-FashionSigLIP QA engine — fashion-domain image understanding.

The color+cropsize confidence was blind to shape/fit/material/type errors
(the user's "slim fit not oversized", "blazer not tunic", wool-vs-smooth
downvotes, all at high self-confidence). This uses a fashion-tuned SigLIP
(Apache-2.0, ViT-B-16, ~150M) to give three signals the old system lacked:

  match  = cosine(embed source-garment cutout, embed render)  -> holistic
           "is the render the same garment" (type/shape/fit/material/color).
  attrs  = zero-shot probes on the RENDER: oversized vs slim, wool vs smooth,
           collar vs collarless ... vs what the description claims.
  margin = the source cutout's top-archetype confidence margin -> a REAL
           perception-confidence (low margin = the crop was ambiguous, the
           "too confident, we didn't see much" fix).

`validate` correlates the signals with the user's up/down ratings before we
trust them. `score_all` writes fashion_qa.json for the rating page.

VALIDATION VERDICT (2026-07-14, negative result — kept, NOT wired as a gate):
Tested 4 ways against the 56 ratings; none reliably separates up/down:
  1. image-image cosine (cutout vs render):  up 0.591 / down 0.535, F1 0.36
  2. attribute divergence (cat-scoped):        up 0.96  / down 2.00,  F1 0.38
  3. description-anchored fit probe:            1 TP / 6 FP
  4. archetype-retrieval top1-top2 margin:     up 0.0080 / down 0.0076 (none)
Root cause: the SOURCE is a 245px warm-cast, often-occluded thumbnail — even a
SOTA fashion model can't extract clean shape/fit/material signal from it
(matches the user's own "too confident, we didn't see much"). The reliable
automated signal remains the deterministic color check (confidence.py, 3/3,
0 FP). The evidence-based fix for the rest is full-resolution source photos.
Embedding helpers here are reusable if better inputs arrive.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review" / "garments_omini"
SHOTS = OUT / "shots"
CONDS = OUT / "conditions"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
MODEL = "hf-hub:Marqo/marqo-fashionSigLIP"

_model = None
_preprocess = None
_tokenizer = None


def _load():
    global _model, _preprocess, _tokenizer
    if _model is None:
        import open_clip
        import torch
        print(f"loading {MODEL} ...", flush=True)
        _model, _, _preprocess = open_clip.create_model_and_transforms(MODEL)
        _tokenizer = open_clip.get_tokenizer(MODEL)
        _model.eval()
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        _model.to(dev)
        print(f"model ready on {dev}", flush=True)
    return _model, _preprocess, _tokenizer


def embed_image(path: Path):
    import torch
    from PIL import Image
    model, preprocess, _ = _load()
    dev = next(model.parameters()).device
    x = preprocess(Image.open(path).convert("RGB")).unsqueeze(0).to(dev)
    with torch.no_grad():
        f = model.encode_image(x, normalize=True)
    return f


def embed_texts(texts: list[str]):
    import torch
    model, _, tok = _load()
    dev = next(model.parameters()).device
    t = tok(texts).to(dev)
    with torch.no_grad():
        f = model.encode_text(t, normalize=True)
    return f


def match_score(cond: Path, shot: Path) -> float:
    a = embed_image(cond)
    b = embed_image(shot)
    return float((a @ b.T).item())


# attribute axes as contrastive text-prompt pairs, SCOPED to the categories
# where they carry meaning (a bag has no sleeve). Source-vs-render disagreement
# on a scoped axis = a mismatch signal.
AXES = {
    "fit": ("an oversized loose baggy garment", "a slim fitted tight garment"),
    "silhouette": ("a structured tailored stiff garment", "a soft flowy draped garment"),
    "material": ("a chunky knit ribbed wool garment", "a smooth flat woven fabric garment"),
    "collar": ("a top with a collar or lapels", "a collarless round-neck top"),
    "sleeve": ("a sleeveless top", "a long-sleeved top"),
    "bag_shape": ("a structured stiff boxy bag", "a soft slouchy unstructured bag"),
    "bag_close": ("a bag with a front flap cover", "an open-top or zip bag"),
}
_SCOPE = {
    "top": ("fit", "silhouette", "material", "collar", "sleeve"),
    "dress": ("fit", "silhouette", "material", "sleeve"),
    "outerwear": ("fit", "silhouette", "material", "collar", "sleeve"),
    "bottom": ("fit", "silhouette", "material"),
    "bag": ("bag_shape", "bag_close"),
    "shoes": (), "hijab": ("material",), "accessory": (),
}


def _pole(img_feat, axis) -> int:
    pos, neg = embed_texts(list(AXES[axis]))
    return 0 if float((img_feat @ pos.T).item()) >= float((img_feat @ neg.T).item()) else 1


def divergence(cond: Path, shot: Path, category: str = "top") -> tuple[int, list]:
    axes = _SCOPE.get(category, ("fit", "silhouette", "material"))
    if not axes:
        return 0, []
    cf, sf = embed_image(cond), embed_image(shot)
    diffs = [ax for ax in axes if _pole(cf, ax) != _pole(sf, ax)]
    return len(diffs), diffs


def validate() -> None:
    """Does source-vs-render ATTRIBUTE divergence separate up/down ratings?"""
    import numpy as np
    ratings = json.loads(
        Path("C:/Users/USER/Downloads/garment-ratings (2).json").read_text(encoding="utf-8"))["results"]
    ups, downs, rows = [], [], []
    for r in ratings:
        sid = r["id"]
        cond, shot = CONDS / f"{sid}.png", SHOTS / f"{sid}.png"
        if not (cond.exists() and shot.exists()):
            continue
        n, diffs = divergence(cond, shot, r.get("category", "top"))
        m = match_score(cond, shot)
        rows.append((n, m, r["rating"], sid, r.get("note", ""), diffs))
        (ups if r["rating"] == "up" else downs).append(n)
    print(f"\nattribute divergence (# axes source!=render): "
          f"up mean {np.mean(ups):.2f}, down mean {np.mean(downs):.2f}")
    # sort by divergence desc, then ascending match
    rows.sort(key=lambda x: (-x[0], x[1]))
    print("\n--- MOST-DIVERGENT 16 (should be dense with downvotes) ---")
    for n, m, rating, sid, note, diffs in rows[:16]:
        mark = "DOWN" if rating == "down" else "up  "
        print(f"  div={n} m={m:.2f} [{mark}] {sid}  {','.join(diffs)}  {note[:30]}")
    for thr in (1, 2, 3):
        tp = sum(1 for n in downs if n >= thr)
        fp = sum(1 for n in ups if n >= thr)
        prec = tp / (tp + fp) if (tp + fp) else 0
        rec = tp / len(downs) if downs else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0
        print(f"\ndivergence >= {thr}: flags {tp}/{len(downs)} downvotes, "
              f"{fp}/{len(ups)} false pos (prec {prec:.2f} rec {rec:.2f} F1 {f1:.2f})")


def score_all() -> None:
    ratings_shots = sorted(SHOTS.glob("*.png"))
    out = {}
    for shot in ratings_shots:
        sid = shot.stem
        cond = CONDS / f"{sid}.png"
        if not cond.exists():
            continue
        out[sid] = {"match": round(match_score(cond, shot), 3)}
        print(f"  {sid}: match {out[sid]['match']}", flush=True)
    (OUT / "fashion_qa.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'fashion_qa.json'} ({len(out)} shots)")


if __name__ == "__main__":
    if "--score" in sys.argv:
        score_all()
    else:
        validate()
