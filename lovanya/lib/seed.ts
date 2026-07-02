import { colorName } from "./color";
import type { Category, WardrobeItem } from "./types";

/**
 * The demo closet — a full capsule wardrobe sliced from the reference grid
 * into individual photos under /public/wardrobe. Colors here are sampled from
 * each real image (see scripts/slice-wardrobe.ps1), so harmony scoring and
 * recommendations reason about what's actually in the picture.
 * "Start fresh" in settings clears it.
 */

type Row = [num: number, primary: string, secondary: string];

interface Panel {
  key: string; // /wardrobe/<key>/<num>.png
  cat: Category;
  nouns: string[];
  rows: Row[];
}

const PANELS: Panel[] = [
  {
    key: "top",
    cat: "top",
    nouns: [
      "blouse",
      "tee",
      "striped shirt",
      "knit tank",
      "bow blouse",
      "cardigan",
      "linen shirt",
      "puff blouse",
      "knit top",
      "one-shoulder top",
    ],
    rows: [
      [1, "#ede8e0", "#e5ddd2"],
      [2, "#262521", "#0f0f0b"],
      [3, "#bac4d8", "#9caac4"],
      [4, "#e5d2c0", "#dbbca9"],
      [5, "#e5baae", "#d29688"],
      [6, "#e4c798", "#d6b076"],
      [7, "#aeac8e", "#898661"],
      [8, "#ebe5dd", "#e0d8cd"],
      [9, "#987f6e", "#6e5340"],
      [10, "#43423e", "#0e0d09"],
    ],
  },
  {
    key: "dress",
    cat: "dress",
    nouns: [
      "wrap dress",
      "puff-sleeve dress",
      "slip dress",
      "floral dress",
      "shirt dress",
      "midi dress",
      "button dress",
      "tiered dress",
      "slip dress",
      "square-neck dress",
    ],
    rows: [
      [1, "#eadfd1", "#dac7b0"],
      [2, "#ccd1d8", "#a7b1bf"],
      [3, "#676561", "#13120d"],
      [4, "#e0d7cc", "#c4b5a4"],
      [5, "#bfbda8", "#918f71"],
      [6, "#e3beb7", "#cd8f85"],
      [7, "#ddccbc", "#c5ab92"],
      [8, "#ac826b", "#71371a"],
      [9, "#ada794", "#5c5333"],
      [10, "#6e6c68", "#0f0d0a"],
    ],
  },
  {
    key: "bottom",
    cat: "bottom",
    nouns: [
      "wide jeans",
      "tailored trousers",
      "trousers",
      "straight jeans",
      "pleated skirt",
      "pleated skirt",
      "shorts",
      "wide trousers",
      "relaxed trousers",
      "denim skirt",
    ],
    rows: [
      [1, "#9bacb6", "#7a8f9b"],
      [2, "#ded1c2", "#ccbaa6"],
      [3, "#393834", "#0e0e0a"],
      [4, "#b6bec0", "#96a2a6"],
      [5, "#d7c0a8", "#bfa182"],
      [6, "#3d3b37", "#11100c"],
      [7, "#eae6df", "#e0d9d0"],
      [8, "#766253", "#4e3827"],
      [9, "#b2af93", "#938f6d"],
      [10, "#e7dfd4", "#d8cdbd"],
    ],
  },
  {
    key: "outerwear",
    cat: "outerwear",
    nouns: [
      "trench coat",
      "denim jacket",
      "blazer",
      "tweed jacket",
      "utility jacket",
      "blazer",
      "jacket",
      "wool coat",
      "leather jacket",
      "puffer",
    ],
    rows: [
      [1, "#d0b79e", "#b39374"],
      [2, "#77878f", "#425560"],
      [3, "#494743", "#12110d"],
      [4, "#e1d7ca", "#bfb19f"],
      [5, "#847c65", "#4a4125"],
      [6, "#a29081", "#6d5845"],
      [7, "#dac8b8", "#c0a891"],
      [8, "#bd9f83", "#8e6a48"],
      [9, "#686560", "#14130e"],
      [10, "#e4d8ca", "#cbb7a0"],
    ],
  },
  {
    key: "shoes",
    cat: "shoes",
    nouns: [
      "sneakers",
      "cap-toe flats",
      "loafers",
      "slingback heels",
      "ankle boots",
      "high-top sneakers",
      "heeled sandals",
      "sneakers",
      "pumps",
      "boots",
    ],
    rows: [
      [1, "#e2ddd6", "#cac3b8"],
      [2, "#b5a390", "#5d432c"],
      [3, "#6f6a63", "#181713"],
      [4, "#d9cdbf", "#b0987f"],
      [5, "#806a5d", "#3e2211"],
      [6, "#8e8b86", "#171713"],
      [7, "#d6c0aa", "#b38e6c"],
      [8, "#cdc8c0", "#9d958b"],
      [9, "#8a8279", "#14120e"],
      [10, "#d3c6b8", "#9e8b77"],
    ],
  },
  {
    key: "bag",
    cat: "bag",
    nouns: [
      "crossbody bag",
      "tote",
      "shoulder bag",
      "hobo bag",
      "top-handle bag",
      "top-handle bag",
      "straw tote",
      "shoulder bag",
      "quilted bag",
      "shoulder bag",
    ],
    rows: [
      [1, "#797671", "#171612"],
      [2, "#d5bda3", "#ba9873"],
      [3, "#a0958e", "#362318"],
      [4, "#ebe2d8", "#d5c5b1"],
      [5, "#84746a", "#331d11"],
      [6, "#e3c5bd", "#ca968b"],
      [7, "#ccaf90", "#9c6b3e"],
      [8, "#cac7b7", "#888565"],
      [9, "#74726d", "#13120e"],
      [10, "#dbd7d1", "#aba49a"],
    ],
  },
  {
    key: "extras",
    cat: "accessory",
    nouns: [
      "cap",
      "bucket hat",
      "scarf",
      "belt",
      "cap",
      "sunglasses",
      "claw clip",
      "baseball cap",
      "scrunchie",
      "pouch",
    ],
    rows: [
      [1, "#d1c0ac", "#b39f87"],
      [2, "#383733", "#11100c"],
      [3, "#dbc4ab", "#c1a17f"],
      [4, "#534e46", "#171612"],
      [5, "#7f6958", "#563e2c"],
      [6, "#5d5b59", "#151512"],
      [7, "#dfc2a5", "#cba076"],
      [8, "#404e42", "#1d2c21"],
      [9, "#cbb8a4", "#aa8f76"],
      [10, "#383733", "#171612"],
    ],
  },
  {
    key: "accessories",
    cat: "accessory",
    nouns: [
      "pendant necklace",
      "hoop earrings",
      "layered necklace",
      "sunglasses",
      "watch",
      "bracelet",
      "pearl earrings",
      "ring",
      "scrunchie",
      "cuff",
    ],
    rows: [
      [1, "#eee5da", "#d7c4a7"],
      [2, "#dbc9b0", "#a9895f"],
      [3, "#efe8df", "#dccdb7"],
      [4, "#958e86", "#2f241c"],
      [5, "#e0d7ca", "#b39e7f"],
      [6, "#eee3d5", "#d7be98"],
      [7, "#e9e0d5", "#d3c2ac"],
      [8, "#e6d6c1", "#caa87c"],
      [9, "#e0d5c6", "#c8b59e"],
      [10, "#efe6da", "#dac5a7"],
    ],
  },
];

// Per-item tuning, keyed by `${key}-${num}`. Anything unset uses the
// category default below — sensible, not exhaustive.
const FORMALITY: Record<string, 1 | 2 | 3> = {
  "top-2": 1,
  "top-4": 1,
  "top-9": 1,
  "bottom-1": 1,
  "bottom-4": 1,
  "bottom-7": 1,
  "bottom-10": 1,
  "bottom-2": 3,
  "bottom-3": 3,
  "bottom-8": 3,
  "outerwear-2": 1,
  "outerwear-5": 1,
  "outerwear-10": 1,
  "outerwear-3": 3,
  "outerwear-4": 3,
  "outerwear-6": 3,
  "shoes-1": 1,
  "shoes-6": 1,
  "shoes-8": 1,
  "shoes-4": 3,
  "shoes-9": 3,
  "dress-3": 3,
  "dress-9": 3,
};

const WARMTH: Record<string, 1 | 2 | 3> = {
  "top-6": 2,
  "top-9": 2,
  "outerwear-1": 3,
  "outerwear-8": 3,
  "outerwear-9": 3,
  "outerwear-10": 3,
};

// Pieces that aren't coverage-friendly, so modest styling can filter them out.
const NON_MODEST = new Set([
  "top-4",
  "top-10",
  "dress-3",
  "dress-9",
  "bottom-7",
]);

const DEFAULT_WARMTH: Record<Category, 1 | 2 | 3> = {
  top: 1,
  dress: 1,
  bottom: 2,
  outerwear: 2,
  shoes: 1,
  bag: 1,
  accessory: 1,
};

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const seededAt = Date.now();

export const SEED_ITEMS: WardrobeItem[] = PANELS.flatMap((panel) =>
  panel.rows.map(([num, primary, secondary]): WardrobeItem => {
    const id = `${panel.key}-${num}`;
    return {
      id: `seed-${id}`,
      name: `${cap(colorName(primary))} ${panel.nouns[num - 1]}`,
      category: panel.cat,
      colors: [primary, secondary],
      warmth: WARMTH[id] ?? DEFAULT_WARMTH[panel.cat],
      formality: FORMALITY[id] ?? 2,
      modest: !NON_MODEST.has(id),
      photo: `/wardrobe/${panel.key}/${num}.png`,
      timesWorn: 0,
      loved: false,
      addedAt: seededAt,
    };
  })
);
