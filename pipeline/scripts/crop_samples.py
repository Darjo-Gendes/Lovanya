"""One-off helper: slice a grid/collage screenshot into individual photos.

Usage:
    python scripts/crop_samples.py <path-to-grid-image> [--out samples]

Detects near-white/uniform gutter rows and columns to find cell boundaries
rather than assuming a perfectly even grid, since collages often have
slightly uneven cell sizes.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def _find_bands(is_gutter: np.ndarray):
    """Given a boolean array marking gutter pixels, return (start, end)
    ranges of the non-gutter content bands in between."""
    bands = []
    in_band = False
    start = 0
    for i, gutter in enumerate(is_gutter):
        if not gutter and not in_band:
            start = i
            in_band = True
        elif gutter and in_band:
            bands.append((start, i))
            in_band = False
    if in_band:
        bands.append((start, len(is_gutter)))
    return bands


def detect_grid(image: Image.Image, min_cell_frac=0.05):
    arr = np.asarray(image.convert("RGB")).astype(int)
    h, w, _ = arr.shape

    col_mean = arr.mean(axis=(0, 2))
    col_std = arr.std(axis=(0, 2))
    row_mean = arr.mean(axis=(1, 2))
    row_std = arr.std(axis=(1, 2))

    col_gutter = (col_mean > 235) & (col_std < 12)
    row_gutter = (row_mean > 235) & (row_std < 12)

    col_bands = [b for b in _find_bands(col_gutter) if (b[1] - b[0]) > w * min_cell_frac]
    row_bands = [b for b in _find_bands(row_gutter) if (b[1] - b[0]) > h * min_cell_frac]

    return row_bands, col_bands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", help="Path to the grid/collage image")
    parser.add_argument("--out", default=None, help="Output directory (default: <pipeline>/samples)")
    parser.add_argument("--pad", type=int, default=2, help="Pixels to trim off each cell edge")
    args = parser.parse_args()

    src = Path(args.image)
    if not src.exists():
        sys.exit(f"Not found: {src}")

    out_dir = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    im = Image.open(src)
    row_bands, col_bands = detect_grid(im)

    print(f"Detected {len(row_bands)} rows x {len(col_bands)} cols = {len(row_bands) * len(col_bands)} cells")

    count = 0
    for r, (y0, y1) in enumerate(row_bands):
        for c, (x0, x1) in enumerate(col_bands):
            box = (x0 + args.pad, y0 + args.pad, x1 - args.pad, y1 - args.pad)
            cell = im.crop(box)
            out_path = out_dir / f"sample_r{r + 1}c{c + 1}.jpg"
            cell.convert("RGB").save(out_path, quality=92)
            count += 1

    print(f"Wrote {count} images to {out_dir}")


if __name__ == "__main__":
    main()
