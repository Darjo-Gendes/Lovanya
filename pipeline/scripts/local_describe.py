"""Local Qwen3-VL garment describe v2 — two-pass, archetype-anchored.

v1 (single pass) proved the concept but lost shape truth in the text
bottleneck: the bag rendered portrait because nobody wrote "landscape", and
the occluded trousers + watch were missed entirely. v2 fixes both:

  PASS 1  whole photo -> exhaustive garment DETECTION with bounding boxes
          (Qwen3-VL grounding), strict anti-false-positive rules, explicit
          recall sweeps (wrists, ears/neck, lower body behind long layers).
  PASS 2  per-garment ZOOMED CROP -> category-specific attribute checklist +
          archetype menu injected from framework/garment-archetypes.md; the
          model snaps to the closest archetype and writes a render prompt
          anchored to its vetted phrase.

Output stays flux_shots.py-compatible: [{item, category, color, prompt, ...}]
in review/garments_flux/descriptions/{stem}.json; crops saved next to it for
box verification.

Usage:
  python pipeline/scripts/local_describe.py b2_r1c4 [more stems...]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import torch
from PIL import Image
from qwen_vl_utils import process_vision_info
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402  (pipeline/config.py)

SAMPLES = ROOT / "samples"
OUT = ROOT / "review" / "garments_flux" / "descriptions"
CROPS = OUT / "crops"
TAXONOMY = ROOT / "framework" / "garment-archetypes.md"

CATEGORIES = ("hijab", "top", "bottom", "dress", "outerwear", "bag", "shoes", "accessory")

DETECT_PROMPT = """You are locating garments in an outfit photo for a modest-fashion service.
Find EVERY clothing item and accessory the PERSON is WEARING or CARRYING, each with a bounding box.

NEVER report (not clothing): walls, curtains, bed, bedding, pillows, furniture, floor, plants, the mirror or its frame, the person's hair/skin/face/hands, a held phone, reflections, shadows.

Recall sweeps - check each deliberately, including partially hidden items:
- head: hijab/headscarf (almost always present here)
- torso: EVERY genuine layer separately (shirt/kemeja under a sweater or vest, top under a blazer/coat)
- lower body: the person IS wearing something below the waist - trousers, skirt, or a dress. Find it and include it even if an open coat hides most of it and only a sliver shows between or below the coat (mark it occluded). Only skip if the photo is cropped above the waist.
- hands/wrists: watch, bracelets - include even if only a few pixels of a band or glint on the wrist
- face/ears/neck: glasses, earrings, necklace
- carried: bag - box the bag's BODY (the pouch itself, usually at hip/waist height); include the strap only as part of that box, NEVER box the strap alone. Shoes if visible.
A hand, phone, strap, or hair crossing OVER a garment does not split it - one garment, one box around everything that belongs to it. When unsure if something is a separate layer, choose FEWER items.

Return a JSON array only. Each element:
{"item": "short name", "category": "hijab|top|bottom|dress|outerwear|bag|shoes|accessory", "bbox_2d": [x1, y1, x2, y2], "occluded": "no | partially (by what)"}
Coordinates are pixels in this image, x1<x2, y1<y2, box snug around the item including hidden extent."""

PASS2_TEMPLATE = """You are capturing ONE garment for a text-to-image model that will recreate it as a standalone product photo from your text ALONE - it never sees these photos.
You get TWO images: IMAGE 1 is the full outfit photo (context). IMAGE 2 is a zoomed crop of your subject: the {item} ({category}). The crop may be badly framed - if it shows only part of the item (e.g. just a strap), find the WHOLE item in image 1 and describe that.
The full outfit also contains: {context}. Describe ONLY the {item}.

COLOR CALIBRATION: the photo has a warm lighting cast. Judge the item's TRUE color using image 1 for reference - a white or cream garment under warm light is still white/cream, NOT beige. Distinguish the item's color from adjacent garments (e.g. a dark bag against a beige coat stays dark).

{occlusion_note}

=== CATEGORY GUIDE (checklist + archetypes) ===
{taxonomy_section}

=== YOUR TASK ===
1. Fill EVERY checklist field above with what you SEE. If a field is hidden, write "not visible (inferred: <most plausible default>)". If the crop is too small/blurry for a field, say "unclear" - do not invent specifics.
2. Pick the CLOSEST archetype from the list. The instance's differences (color, fabric, hardware, pattern) go in the fields - do not invent a new shape.
3. color: plain shade name with undertone AND an approximate hex guess, e.g. "warm sand beige (~#D2B48C)".
4. prompt: ONE sentence, 20-45 words, STARTING from the chosen archetype's render phrase, then this instance's color, material and distinctive details. Plain color name, NO hex. Garment only - no person, no pose, no background.

Return a single JSON object only:
{{"item": "...", "category": "{category}", "archetype": "...", "color": "...",
"attributes": {{ one key per checklist field }},
"details": "distinctive specifics, inferred parts flagged",
"prompt": "..."}}"""


# ---------------------------------------------------------------- taxonomy --
def taxonomy_sections() -> dict[str, str]:
    text = TAXONOMY.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for m in re.finditer(r"^## (\w+)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        sections[m.group(1).strip()] = m.group(2).strip()
    return sections


# ------------------------------------------------------------------ parsing --
def _strip_fences(text: str) -> str:
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return fence.group(1).strip() if fence else text.strip()


def parse_array(raw: str) -> list[dict]:
    text = _strip_fences(raw)
    s, e = text.find("["), text.rfind("]")
    if s != -1 and e > s:
        text = text[s:e + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return [{"_parse_error": True, "_raw": raw}]


def parse_object(raw: str) -> dict:
    text = _strip_fences(raw)
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        text = text[s:e + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_parse_error": True, "_raw": raw}


# -------------------------------------------------------------------- model --
_model = None
_proc = None


def _load():
    global _model, _proc
    if _model is None:
        mid = config.QWEN_MODEL_ID
        print(f"loading {mid} (NF4)...", flush=True)
        _model = AutoModelForImageTextToText.from_pretrained(
            mid, dtype="auto", device_map={"": 0},
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16))
        _proc = AutoProcessor.from_pretrained(mid)
        print("model ready", flush=True)
    return _model, _proc


def ask(image, prompt: str, max_new_tokens: int) -> str:
    """image: one PIL/path or a list of them (multi-image message)."""
    model, proc = _load()
    images = image if isinstance(image, list) else [image]
    content = [{"type": "image", "image": im} for im in images]
    content.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": content}]
    chat = proc.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    imgs, vids = process_vision_info(messages)
    inputs = proc(text=[chat], images=imgs, videos=vids, padding=True,
                  return_tensors="pt").to(model.device)
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, out)]
    return proc.batch_decode(trimmed, skip_special_tokens=True)[0]


# -------------------------------------------------------------------- crops --
def crop_garment(im: Image.Image, bbox, pad: float = 0.12, min_side: int = 448,
                 pad_bottom: float | None = None) -> Image.Image:
    w, h = im.size
    try:
        x1, y1, x2, y2 = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return im  # bad box -> pass 2 sees the whole photo
    # Qwen3-VL grounding emits 0-1000 normalized coords; our samples are tiny
    # (245px), so any coord past the image edge means "normalized" - rescale.
    if max(x1, y1, x2, y2) > max(w, h) + 2:
        x1, x2 = x1 * w / 1000, x2 * w / 1000
        y1, y2 = y1 * h / 1000, y2 * h / 1000
    if x2 <= x1 or y2 <= y1:
        return im
    px, py = (x2 - x1) * pad, (y2 - y1) * pad
    pb = (y2 - y1) * (pad_bottom if pad_bottom is not None else pad)
    x1, y1 = max(0, int(x1 - px)), max(0, int(y1 - py))
    x2, y2 = min(w, int(x2 + px)), min(h, int(y2 + pb))
    if x2 - x1 < 4 or y2 - y1 < 4:
        return im  # degenerate after clamping -> whole photo beats a crash
    crop = im.crop((x1, y1, x2, y2))
    # tiny sources (our samples are collage cells) -> upscale so the VLM's
    # patch grid actually resolves hardware, seams, proportions
    cw, ch = crop.size
    if min(cw, ch) < min_side and min(cw, ch) > 0:
        sc = min_side / min(cw, ch)
        crop = crop.resize((int(cw * sc), int(ch * sc)), Image.LANCZOS)
    return crop


# --------------------------------------------------------------------- main --
def describe(stem: str) -> list[dict]:
    img_path = SAMPLES / f"{stem}.jpg"
    im = Image.open(img_path).convert("RGB")
    sections = taxonomy_sections()

    t0 = time.time()
    raw = ask(str(img_path), DETECT_PROMPT, max_new_tokens=700)
    detected = [d for d in parse_array(raw)
                if d.get("category") in CATEGORIES and not d.get("_parse_error")]
    print(f"pass1: {len(detected)} items in {time.time()-t0:.0f}s: "
          + ", ".join(d.get("item", "?") for d in detected), flush=True)
    if not detected:
        print(f"  pass1 raw output was: {raw[:400]}", flush=True)
        return []

    CROPS.mkdir(parents=True, exist_ok=True)
    context = ", ".join(d.get("item", "?") for d in detected)
    results = []
    for i, det in enumerate(detected):
        # pass 1 tends to box a bag's STRAP; the body hangs below it, so bags
        # get a much wider crop extended hard downward
        is_bag = det.get("category") == "bag"
        crop = crop_garment(im, det.get("bbox_2d"),
                            pad=0.35 if is_bag else 0.12,
                            pad_bottom=0.9 if is_bag else None)
        crop_file = CROPS / f"{stem}_{i}_{det.get('category')}.jpg"
        crop.convert("RGB").save(crop_file, "JPEG", quality=90)
        occ = det.get("occluded", "no")
        occ_note = ("Parts of this garment are hidden " + f"({occ}). Describe the visible part; infer hidden parts as the most plausible default and flag them."
                    if occ and occ != "no" else
                    "The garment appears fully visible; describe what you see.")
        if is_bag:
            occ_note += (" BAG SHAPE JUDGMENT: a leather flap bag holds a firm rectangular "
                         "silhouette - only call it slouchy/hobo if the body VISIBLY slumps "
                         "into a crescent. Verify orientation (wider-than-tall vs "
                         "taller-than-wide) against the full photo in image 1, not the crop.")
        prompt = PASS2_TEMPLATE.format(
            item=det.get("item", "garment"), category=det.get("category"),
            context=context, occlusion_note=occ_note,
            taxonomy_section=sections.get(det.get("category"), "(no guide)"))
        t = time.time()
        raw2 = ask([str(img_path), crop], prompt, max_new_tokens=800)
        rec = parse_object(raw2)
        rec.setdefault("item", det.get("item"))
        rec.setdefault("category", det.get("category"))
        rec["bbox"] = det.get("bbox_2d")
        rec["occluded"] = occ
        results.append(rec)
        ok = "PARSE-ERR" if rec.get("_parse_error") else rec.get("archetype", "?")
        print(f"  pass2 [{i}] {det.get('item','?')}: {ok} ({time.time()-t:.0f}s)", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{stem}.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{stem}: {len(results)} garments -> {OUT / f'{stem}.json'}", flush=True)
    return results


def main() -> None:
    stems = [a for a in sys.argv[1:] if not a.startswith("--")] or ["b2_r1c4"]
    force = "--force" in sys.argv
    for stem in stems:
        if not (SAMPLES / f"{stem}.jpg").exists():
            print(f"  {stem}: sample missing", flush=True)
            continue
        if not force and (OUT / f"{stem}.json").exists():
            print(f"  {stem}: description cached, skipping", flush=True)
            continue
        describe(stem)


if __name__ == "__main__":
    main()
