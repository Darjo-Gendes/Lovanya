import { colorName } from "./color";
import type { GarmentMetrics, OutfitInput } from "./lookcard";
import { CATEGORIES, type Category, type Occasion, OCCASIONS, type WardrobeItem } from "./types";

/**
 * JSON → garments boundary (visual-pipeline-v1 §Contracts).
 *
 * A "look file" is the interchange between the pipeline and the renderer:
 * the GPU pipeline emits garments + outfits as JSON, the UI renders LookCards
 * from it with no code in between. Two garment shapes are accepted:
 *
 *   app shape        { colors: ["#…", "#…"] }
 *   canonical shape  { color_primary: "#…", color_secondary: "#…" }   // pipeline/app/contracts.py Garment
 *
 * Everything is validated here at the boundary; invalid entries are skipped
 * and reported in `errors`, never thrown mid-render.
 */

export interface LookFile {
  garments: WardrobeItem[];
  outfits: OutfitInput[];
  errors: string[];
}

/** Fixed fallback so a file without timestamps still renders deterministically. */
const DEFAULT_AT = Date.UTC(2026, 0, 1, 12);

const VALID_CATEGORIES = new Set<string>(CATEGORIES.map((c) => c.id));
const VALID_OCCASIONS = new Set<string>(OCCASIONS.map((o) => o.id));
const HEX = /^#[0-9a-fA-F]{6}$/;

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/* eslint-disable @typescript-eslint/no-explicit-any */

function readColors(g: any): string[] {
  const out: string[] = [];
  const push = (c: unknown) => {
    if (typeof c === "string" && HEX.test(c) && !out.includes(c)) out.push(c);
  };
  if (Array.isArray(g.colors)) g.colors.forEach(push);
  push(g.color_primary);
  push(g.color_secondary);
  return out;
}

/** Canonical formality strings → the app's 1–3 scale (numbers pass through). */
function readFormality(v: unknown): 1 | 2 | 3 {
  if (v === 1 || v === 2 || v === 3) return v;
  if (v === "casual") return 1;
  if (v === "formal") return 3;
  return 2; // smart-casual / business / unknown
}

function readWarmth(v: unknown): 1 | 2 | 3 {
  return v === 1 || v === 2 || v === 3 ? v : 1;
}

function readMetrics(g: any): GarmentMetrics | undefined {
  const clarity = typeof g.clarity === "number" ? Math.min(Math.max(g.clarity, 0), 1) : undefined;
  const dominance = typeof g.dominance === "number" ? Math.min(Math.max(g.dominance, 0), 1) : undefined;
  if (clarity === undefined && dominance === undefined) return undefined;
  return { clarity, dominance };
}

function parseGarment(
  g: any,
  index: number,
  errors: string[]
): { item: WardrobeItem; metrics?: GarmentMetrics } | null {
  if (typeof g !== "object" || g === null) {
    errors.push(`garment[${index}]: not an object — skipped`);
    return null;
  }
  const id = typeof g.id === "string" && g.id ? g.id : `json-${index}`;
  if (!VALID_CATEGORIES.has(g.category)) {
    errors.push(`garment[${index}] (${id}): unknown category "${g.category}" — skipped`);
    return null;
  }
  const colors = readColors(g);
  if (colors.length === 0) {
    errors.push(`garment[${index}] (${id}): no valid hex colors — skipped`);
    return null;
  }

  const photo =
    typeof g.cutout_url === "string" && g.cutout_url
      ? g.cutout_url
      : typeof g.image_url === "string" && g.image_url
        ? g.image_url
        : undefined;

  const noun =
    typeof g.subcategory === "string" && g.subcategory ? g.subcategory : g.category;
  const name =
    typeof g.name === "string" && g.name ? g.name : `${cap(colorName(colors[0]))} ${noun}`;

  const item: WardrobeItem = {
    id,
    name,
    category: g.category as Category,
    colors,
    warmth: readWarmth(g.warmth),
    formality: readFormality(g.formality),
    modest: typeof g.modest === "boolean" ? g.modest : true,
    photo,
    timesWorn: 0,
    loved: g.loved === true,
    addedAt: typeof g.added_at === "number" ? g.added_at : DEFAULT_AT,
  };
  return { item, metrics: readMetrics(g) };
}

/**
 * Parse a look file (already JSON.parse'd). Never throws — malformed entries
 * are skipped with a message in `errors`.
 */
export function parseLookFile(data: unknown): LookFile {
  const errors: string[] = [];
  const root = (typeof data === "object" && data !== null ? data : {}) as any;
  if (typeof data !== "object" || data === null) {
    errors.push("file root is not an object");
  }

  const metricsById: Record<string, GarmentMetrics> = {};
  const garments: WardrobeItem[] = [];
  const rawGarments = Array.isArray(root.garments) ? root.garments : [];
  if (!Array.isArray(root.garments)) errors.push('missing "garments" array');
  rawGarments.forEach((g: any, i: number) => {
    const parsed = parseGarment(g, i, errors);
    if (!parsed) return;
    if (garments.some((x) => x.id === parsed.item.id)) {
      errors.push(`garment[${i}]: duplicate id "${parsed.item.id}" — skipped`);
      return;
    }
    garments.push(parsed.item);
    if (parsed.metrics) metricsById[parsed.item.id] = parsed.metrics;
  });
  const byId = new Map(garments.map((g) => [g.id, g]));

  const outfits: OutfitInput[] = [];
  const rawOutfits = Array.isArray(root.outfits) ? root.outfits : [];
  rawOutfits.forEach((o: any, i: number) => {
    if (typeof o !== "object" || o === null || !Array.isArray(o.garment_ids)) {
      errors.push(`outfit[${i}]: missing garment_ids — skipped`);
      return;
    }
    const resolved: WardrobeItem[] = [];
    for (const gid of o.garment_ids) {
      const g = byId.get(gid);
      if (g) resolved.push(g);
      else errors.push(`outfit[${i}]: unknown garment id "${gid}" — dropped from outfit`);
    }
    if (resolved.length === 0) {
      errors.push(`outfit[${i}]: no resolvable garments — skipped`);
      return;
    }
    const metrics: Record<string, GarmentMetrics> = {};
    for (const g of resolved) {
      if (metricsById[g.id]) metrics[g.id] = metricsById[g.id];
    }
    outfits.push({
      id: typeof o.id === "string" && o.id ? o.id : `outfit-${i}`,
      garments: resolved,
      occasion: VALID_OCCASIONS.has(o.occasion) ? (o.occasion as Occasion) : undefined,
      title: typeof o.title === "string" && o.title ? o.title : undefined,
      createdAt: typeof o.created_at === "number" ? o.created_at : DEFAULT_AT,
      metrics: Object.keys(metrics).length ? metrics : undefined,
    });
  });

  // A file with garments but no outfits still renders: one single-piece
  // outfit per garment, so any pipeline identify-output is viewable as-is.
  if (outfits.length === 0 && garments.length > 0) {
    for (const g of garments) {
      outfits.push({
        id: `solo-${g.id}`,
        garments: [g],
        createdAt: g.addedAt,
        metrics: metricsById[g.id] ? { [g.id]: metricsById[g.id] } : undefined,
      });
    }
  }

  return { garments, outfits, errors };
}
