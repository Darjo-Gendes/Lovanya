import { hexToRgb } from "./color";
import type { Category, WardrobeItem } from "./types";

/**
 * Duplicate detection — the UI-PC placeholder for the embedding-based dedup in
 * pipeline/docs/visual-pipeline-v1.md (§4). The GPU pipeline will replace the
 * INTERNALS of `findLikelyDuplicate` with cutout-embedding similarity; the
 * signature and the product rule stay: we only ever SUGGEST a match — the user
 * confirms. Never silent-merge (critical rule #6).
 *
 * Heuristic here: same category, then colour distance between the garments'
 * sampled palettes. Deterministic, no model needed.
 */

export interface DuplicateMatch {
  item: WardrobeItem;
  /** 0–1; 1 = visually identical by the current measure. */
  similarity: number;
}

/** Max Euclidean distance in RGB space (√(3·255²)) for normalising. */
const MAX_DIST = Math.sqrt(3 * 255 * 255);

function colorSim(a: string, b: string): number {
  const [r1, g1, b1] = hexToRgb(a);
  const [r2, g2, b2] = hexToRgb(b);
  const d = Math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2);
  return 1 - d / MAX_DIST;
}

function garmentSim(colorsA: string[], colorsB: string[]): number {
  if (!colorsA[0] || !colorsB[0]) return 0;
  const primary = colorSim(colorsA[0], colorsB[0]);
  if (colorsA[1] && colorsB[1]) {
    return primary * 0.75 + colorSim(colorsA[1], colorsB[1]) * 0.25;
  }
  return primary;
}

/**
 * Conservative on purpose: a false suggestion costs one tap ("No, it's new"),
 * but a lax threshold would nag on every similar-coloured piece.
 */
export const DUPLICATE_THRESHOLD = 0.94;

/**
 * Returns the single most similar same-category item at or above the
 * threshold, or null. Ties resolve to the first in stable item order.
 */
export function findLikelyDuplicate(
  draft: { category: Category; colors: string[] },
  items: WardrobeItem[]
): DuplicateMatch | null {
  if (!draft.colors[0]) return null;

  let best: DuplicateMatch | null = null;
  for (const item of items) {
    if (item.category !== draft.category) continue;
    const similarity = garmentSim(draft.colors, item.colors);
    if (similarity >= DUPLICATE_THRESHOLD && (!best || similarity > best.similarity)) {
      best = { item, similarity };
    }
  }
  return best;
}
