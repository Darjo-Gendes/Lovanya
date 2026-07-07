"""Generate an outfit / LookCard image locally on the GPU (no tokens).

First run loads SDXL into VRAM (slow); subsequent images are fast.

Usage (from the repo root):
    python pipeline/gen_lookcard.py "black blazer, white tee, tailored trousers" --occasion "work" --seed 7
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.app.imagegen import generate  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("garments", help="short garment description, e.g. 'red midi dress'")
    p.add_argument("--occasion", default="casual")
    p.add_argument("--colors", default="", help="comma-separated palette, optional")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=28)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    palette = [c.strip() for c in args.colors.split(",") if c.strip()] or None
    t0 = time.time()
    out = generate(args.occasion, args.garments, palette=palette,
                   out_path=args.out, steps=args.steps, seed=args.seed)
    print(f"saved {out} in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
