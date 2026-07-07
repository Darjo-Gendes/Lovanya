"""Render a clean product shot from a garment cutout, locally on the GPU.

First run loads SDXL into VRAM (slow); later renders are fast. The judge model
must NOT be resident at the same time on an 8GB card (co-residency guardrail).

Usage (from the repo root):
    python pipeline/render_shot.py pipeline/review/matte_gpu/x_top_t-shirt.png --desc "black t-shirt"
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.app.imagegen import render_product_shot  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cutout", help="path to a garment cutout image (PNG, transparent ok)")
    p.add_argument("--desc", default="a clothing garment", help="short garment description")
    p.add_argument("--strength", type=float, default=0.4)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    src = Path(args.cutout)
    if not src.exists():
        sys.exit(f"not found: {src}")
    out = Path(args.out) if args.out else src.with_name(src.stem + "_shot.png")

    t0 = time.time()
    shot = render_product_shot(src.read_bytes(), garment_desc=args.desc,
                               strength=args.strength, seed=args.seed)
    out.write_bytes(shot)
    print(f"saved {out} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
