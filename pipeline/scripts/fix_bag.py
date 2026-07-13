"""Bag-specific fidelity bundle — the four fixes, then regenerate the bag.

The bag got the worst input of the set (~30x45px of body through a warm-cast
8KB JPEG) and rigid leather goods are the least forgiving category. Bundle:
  1. cleaned condition: SAM2 mask -> largest connected component only (drops
     the coat-edge sliver), LANCZOS x4 + unsharp instead of mush;
  2. measured color: gray-world white balance, then median-sample the masked
     pixels -> nearest named shade (deterministic, no olive-vs-brown judging);
  3. archetype canonical completion: box-flap crossbody inherits smooth
     leather + gold clasp lock (garment-archetypes.md rule);
  4. condition_scale=1.3: rigid objects follow the reference pixels harder.

Usage: python pipeline/scripts/fix_bag.py b2_r1c4
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import numpy as np
import torch
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))                       # pipeline pkg root (config, app.*)
sys.path.insert(0, str(ROOT.parent))                # repo root for pipeline.app imports
sys.path.insert(0, str(ROOT / "vendor" / "OminiControlGP"))

OUT = ROOT / "review" / "garments_omini"
DESCS = ROOT / "review" / "garments_flux" / "descriptions"
BASE_REPO = "YuCollection/FLUX.1-schnell-Diffusers"
STEM = next((a for a in sys.argv[1:] if not a.startswith("--")), "b2_r1c4")

SHADES = {  # small curated palette -> plain names FLUX understands
    "black": (20, 18, 16), "dark chocolate brown": (60, 42, 30),
    "dark brown": (78, 53, 36), "chestnut brown": (110, 74, 48),
    "tan": (176, 138, 98), "beige": (206, 184, 154),
    "dark olive green": (72, 70, 42), "navy blue": (28, 34, 62),
    "burgundy": (88, 32, 40), "grey": (128, 126, 122), "cream": (238, 230, 210),
}


def gray_world_wb(im: Image.Image) -> Image.Image:
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    means = a.reshape(-1, 3).mean(axis=0)
    a = np.clip(a * (means.mean() / np.maximum(means, 1e-4)), 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def nearest_shade(rgb) -> str:
    r, g, b = rgb
    return min(SHADES, key=lambda k: (SHADES[k][0]-r)**2 + (SHADES[k][1]-g)**2 + (SHADES[k][2]-b)**2)


def largest_component(mask: np.ndarray) -> np.ndarray:
    import cv2
    n, labels = cv2.connectedComponents(mask.astype(np.uint8))
    if n <= 2:
        return mask
    sizes = [(labels == i).sum() for i in range(1, n)]
    return labels == (1 + int(np.argmax(sizes)))


def build_condition_and_color() -> tuple[Image.Image, str, dict]:
    from pipeline.app.cutout import sam2_mask
    garments = json.loads((DESCS / f"{STEM}.json").read_text(encoding="utf-8"))
    idx, bag = next((i, g) for i, g in enumerate(garments) if g.get("category") == "bag")

    src = Image.open(ROOT / "samples" / f"{STEM}.jpg").convert("RGB")
    w, h = src.size
    x1, y1, x2, y2 = [float(v) for v in bag["bbox"]]
    if max(x1, y1, x2, y2) > max(w, h) + 2:          # 0-1000 normalized
        x1, x2 = x1 * w / 1000, x2 * w / 1000
        y1, y2 = y1 * h / 1000, y2 * h / 1000
    bh, bw = y2 - y1, x2 - x1                        # strap-box -> extend to body
    y2 = min(h, y2 + 0.9 * bh)
    x1, x2 = max(0, x1 - 0.35 * bw), min(w, x2 + 0.35 * bw)

    wb = gray_world_wb(src)
    mask = sam2_mask(wb, (x1, y1, x2, y2))
    mask = largest_component(mask)                    # drop coat-sliver contamination

    ys, xs = np.where(mask)
    px = np.asarray(wb)[ys, xs]                       # white-balanced bag pixels
    med = tuple(np.median(px, axis=0))
    shade = nearest_shade(med)
    print(f"measured bag color (WB median): rgb={tuple(int(v) for v in med)} -> '{shade}'", flush=True)

    rgba = wb.convert("RGBA")
    alpha = Image.fromarray((mask * 255).astype(np.uint8), "L").resize(rgba.size)
    rgba.putalpha(alpha)
    x0m, x1m = xs.min(), xs.max()
    y0m, y1m = ys.min(), ys.max()
    cut = rgba.crop((x0m, y0m, max(x0m + 1, x1m), max(y0m + 1, y1m)))
    side = max(cut.size)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    sq.paste(cut, ((side - cut.width) // 2, (side - cut.height) // 2), cut)
    cond = sq.convert("RGB").resize((512, 512), Image.LANCZOS)
    cond = cond.filter(ImageFilter.UnsharpMask(radius=3, percent=120, threshold=2))
    cond_path = OUT / "conditions" / f"{STEM}_{idx}_bag_v2.png"
    cond.save(cond_path)
    print(f"condition image -> {cond_path.name}", flush=True)
    return cond, shade, {"idx": idx, "bag": bag}


def main() -> None:
    cond, shade, meta = build_condition_and_color()
    idx = meta["idx"]

    # archetype canonical render phrase (garment-archetypes.md) + measured color
    prompt = (f"professional e-commerce catalog product photograph of this exact item: "
              f"a structured box-flap crossbody bag in smooth {shade} leather with a slight "
              f"sheen, wide landscape rectangle clearly wider than tall, firm crisp edges "
              f"holding a boxy shape, full-width front flap with a gold metal clasp lock, "
              f"long slim leather shoulder strap. The item is shown alone, upright, centered "
              f"on a pure seamless white background, soft even studio lighting, sharp focus, "
              f"true to the reference item's real color, shape and proportions. No person, "
              f"no body, no mannequin, no props, no text.")
    print(f"PROMPT: {prompt[:140]}...", flush=True)

    from diffusers.pipelines import FluxPipeline
    from src.flux.condition import Condition
    from src.flux.generate import generate, seed_everything

    t0 = time.time()
    pipe = FluxPipeline.from_pretrained(BASE_REPO, torch_dtype=torch.bfloat16)
    pipe.load_lora_weights("Yuanshi/OminiControl",
                           weight_name="omini/subject_512.safetensors",
                           adapter_name="subject")
    from mmgp import offload  # after load: its safetensors patch breaks transformers 5.x
    offload.profile(pipe, profile_no=5, verboseLevel=1, quantizeTransformer=True)
    print(f"pipeline ready in {time.time()-t0:.0f}s", flush=True)

    condition = Condition("subject", cond, position_delta=(0, 32))
    t = time.time()
    seed_everything(42)
    img = generate(pipe, prompt=prompt, conditions=[condition],
                   condition_scale=1.3,
                   num_inference_steps=8, height=512, width=512).images[0]
    out = OUT / "shots" / f"{STEM}_{idx}_bag.png"
    img.save(out)
    print(f"BAG FIXED: {time.time()-t:.0f}s -> {out}", flush=True)


if __name__ == "__main__":
    main()
