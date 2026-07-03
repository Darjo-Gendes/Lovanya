import { colorName } from "./color";
import { OCCASIONS, type Occasion, type WardrobeItem } from "./types";

/**
 * LookCard contract + deterministic builder — the UI-PC half of
 * pipeline/docs/visual-pipeline-v1.md (§Contracts, §Layout rules, §Hero scoring).
 *
 * Everything here is a pure function of its inputs: same outfit in, same card
 * out, every time (critical rule #2). No randomness, no clock reads.
 *
 * Storage is deferred (locked decision #3), so `thumbnailUrl` stays optional
 * and cards are rebuilt from wardrobe state instead of persisted.
 */

export type LookCardLayout = "center" | "diagonal" | "stack" | "grid";

export interface LookCard {
  id: string;
  outfitId: string;
  title: string;
  subtitle: string;
  caption: string;
  layout: LookCardLayout;
  heroGarmentId: string;
  /** Scored order, hero first — the renderer composes in this order. */
  garmentIds: string[];
  palette: string[];
  createdAt: number;
  /** Populated once storage exists (deferred). */
  thumbnailUrl?: string;
}

/**
 * Per-garment metrics the real pipeline supplies once segmentation lands:
 * clarity = normalized sharpness of the cutout, dominance = normalized pixel
 * area of the garment within its outfit photo. Until then the builder uses
 * the deterministic proxies below.
 */
export interface GarmentMetrics {
  clarity?: number;
  dominance?: number;
}

export interface OutfitInput {
  id: string;
  garments: WardrobeItem[];
  occasion?: Occasion;
  /** Overrides the derived title (e.g. Qwen's style_summary later). */
  title?: string;
  createdAt: number;
  /** By garment id; from the pipeline once segmentation lands. */
  metrics?: Record<string, GarmentMetrics>;
}

/** Spec: outerwear > dress > top > bottom > shoes > bag > accessory. */
const CATEGORY_WEIGHT: Record<WardrobeItem["category"], number> = {
  outerwear: 1,
  dress: 0.92,
  top: 0.8,
  bottom: 0.68,
  shoes: 0.55,
  bag: 0.45,
  accessory: 0.35,
};

/** Layout rules (deterministic): 1 → center · 2 → diagonal · 3–4 → stack · 5+ → grid. */
export function selectLayout(garmentCount: number): LookCardLayout {
  if (garmentCount <= 1) return "center";
  if (garmentCount === 2) return "diagonal";
  if (garmentCount <= 4) return "stack";
  return "grid";
}

/** Proxy until segmentation supplies a real sharpness score for the cutout. */
function clarityProxy(item: WardrobeItem): number {
  if (item.photo) return 0.9;
  if (item.art) return 0.55;
  return 0.35;
}

export function heroScore(
  item: WardrobeItem,
  recency: number,
  metrics?: GarmentMetrics
): number {
  const clarity = metrics?.clarity ?? clarityProxy(item);
  const category = CATEGORY_WEIGHT[item.category];
  // Spec: dominance = pixel area × category weight. Area is unknown until
  // segmentation, so the proxy collapses to the category weight alone.
  const dominance = metrics?.dominance ?? category;
  const favorite = item.loved ? 1 : 0;
  return (
    clarity * 0.35 +
    category * 0.25 +
    dominance * 0.2 +
    recency * 0.1 +
    favorite * 0.1
  );
}

/** Newest garment in the outfit → 1, oldest → 0; single garment → 1. */
function recencyRanks(garments: WardrobeItem[]): Map<string, number> {
  const sorted = [...garments].sort((a, b) => a.addedAt - b.addedAt);
  const span = Math.max(sorted.length - 1, 1);
  const ranks = new Map<string, number>();
  sorted.forEach((g, i) => ranks.set(g.id, garments.length === 1 ? 1 : i / span));
  return ranks;
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

const occasionLabel = (o?: Occasion) =>
  o ? OCCASIONS.find((x) => x.id === o)?.label : undefined;

function fmtDate(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Build a LookCard from an outfit. Returns null for an empty outfit —
 * there is nothing to render and no hero to pick.
 */
export function buildLookCard(input: OutfitInput): LookCard | null {
  const garments = input.garments.filter(Boolean);
  if (garments.length === 0) return null;

  const ranks = recencyRanks(garments);
  const scored = [...garments].sort((a, b) => {
    const diff =
      heroScore(b, ranks.get(b.id) ?? 0, input.metrics?.[b.id]) -
      heroScore(a, ranks.get(a.id) ?? 0, input.metrics?.[a.id]);
    if (diff !== 0) return diff;
    return a.id < b.id ? -1 : 1; // stable tiebreak → hero never flips
  });
  const hero = scored[0];

  const palette: string[] = [];
  for (const g of scored) {
    for (const c of g.colors) {
      if (c && !palette.includes(c)) palette.push(c);
      if (palette.length >= 4) break;
    }
    if (palette.length >= 4) break;
  }
  if (palette.length === 0) palette.push("#d8c4bc");

  const names = palette.slice(0, 2).map(colorName);
  const title =
    input.title ??
    (names.length > 1 && names[0] !== names[1]
      ? `${cap(names[0])} & ${names[1]}`
      : cap(names[0]));

  const occ = occasionLabel(input.occasion);
  const subtitle = occ
    ? `${fmtDate(input.createdAt)} · ${occ}`
    : fmtDate(input.createdAt);

  const caption =
    garments.length === 1
      ? `Your ${colorName(hero.colors[0] ?? "#d8c4bc")} ${hero.category} takes the spotlight.`
      : `${cap(colorName(hero.colors[0] ?? "#d8c4bc"))} ${hero.category} anchors a ${garments.length}-piece look.`;

  return {
    id: `lc-${input.id}`,
    outfitId: input.id,
    title,
    subtitle,
    caption,
    layout: selectLayout(garments.length),
    heroGarmentId: hero.id,
    garmentIds: scored.map((g) => g.id),
    palette,
    createdAt: input.createdAt,
  };
}
