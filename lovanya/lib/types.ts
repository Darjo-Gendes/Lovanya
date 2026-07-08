export type Category =
  | "top"
  | "bottom"
  | "dress"
  | "outerwear"
  | "shoes"
  | "bag"
  | "accessory";

export const CATEGORIES: { id: Category; label: string }[] = [
  { id: "top", label: "Tops" },
  { id: "bottom", label: "Bottoms" },
  { id: "dress", label: "Dresses" },
  { id: "outerwear", label: "Outer" },
  { id: "shoes", label: "Shoes" },
  { id: "bag", label: "Bags" },
  { id: "accessory", label: "Extras" },
];

/** Flat-illustration silhouettes used for items without a photo. */
export type GarmentKind =
  | "blouse"
  | "tee"
  | "knit"
  | "blazer"
  | "cardigan"
  | "coat"
  | "dress"
  | "slipdress"
  | "skirt"
  | "trousers"
  | "jeans"
  | "flats"
  | "heels"
  | "sneakers"
  | "tote"
  | "crossbody"
  | "scarf";

/** A re-upload of a piece the user confirmed is the same garment. */
export interface ItemVariant {
  photo?: string;
  addedAt: number;
}

export interface WardrobeItem {
  id: string;
  name: string;
  category: Category;
  /** Dominant colors, most prominent first (hex). */
  colors: string[];
  /** 1 = light/summer, 2 = mid, 3 = warm layer. */
  warmth: 1 | 2 | 3;
  /** 1 = casual, 2 = smart, 3 = dressy. */
  formality: 1 | 2 | 3;
  modest: boolean;
  /** Downscaled photo data-URL for user-added items. */
  photo?: string;
  /** Illustration for seeded items. */
  art?: GarmentKind;
  /** Confirmed duplicates merged into this canonical item (visual-pipeline-v1 §4). */
  variants?: ItemVariant[];
  timesWorn: number;
  loved: boolean;
  addedAt: number;
}

export type Occasion =
  | "work"
  | "class"
  | "casual"
  | "date"
  | "event"
  | "errands";

export const OCCASIONS: { id: Occasion; label: string; emoji: string }[] = [
  { id: "work", label: "Work", emoji: "💼" },
  { id: "class", label: "Class", emoji: "📚" },
  { id: "casual", label: "Casual day", emoji: "🍃" },
  { id: "date", label: "Date", emoji: "🌹" },
  { id: "event", label: "Event", emoji: "✨" },
  { id: "errands", label: "Errands", emoji: "🧺" },
];

export type Mood =
  | "confident"
  | "calm"
  | "playful"
  | "elegant"
  | "comfortable"
  | "chic";

export const MOODS: { id: Mood; label: string }[] = [
  { id: "confident", label: "Confident" },
  { id: "calm", label: "Calm" },
  { id: "comfortable", label: "Comfortable" },
  { id: "elegant", label: "Elegant" },
  { id: "playful", label: "Playful" },
  { id: "chic", label: "Chic" },
];

export interface Weather {
  tempC: number;
  condition: "sunny" | "cloudy" | "rainy" | "breezy";
  label: string;
  blurb: string;
}

export interface OutfitAnalysis {
  /** 0–100 overall confidence score. */
  score: number;
  headline: string;
  palette: string[];
  paletteNames: string[];
  breakdown: { label: string; score: number; note: string }[];
  whatWorks: string[];
  gentleThought: string;
  auraNote: string;
}

export interface Recommendation {
  id: string;
  items: WardrobeItem[];
  score: number;
  title: string;
  why: string[];
  auraNote: string;
}

/**
 * A saved look — the Journal's core entity (evolved from the original check
 * record; every field added for Journal v1 is optional so previously
 * persisted stores keep working untouched).
 */
export interface CheckRecord {
  id: string;
  at: number;
  score: number;
  occasion: Occasion;
  palette: string[];
  headline: string;
  thumb?: string;
  /** User-typed context from the Style Me note input ("Summer brunch…"). */
  title?: string;
  /** Ribbon = "memorable moment" — the single save affordance on looks. */
  ribboned?: boolean;
  /** Wardrobe items filed from this look (canonical ids after dedup). */
  garmentIds?: string[];
  /** Full analysis payload so the Journal can reopen the verdict later. */
  breakdown?: { label: string; score: number; note: string }[];
  whatWorks?: string[];
  gentleThought?: string;
  auraNote?: string;
}

/** Journal-facing alias — same persisted shape, clearer name. */
export type Look = CheckRecord;

export interface Profile {
  name: string;
  vibes: string[];
  modest: boolean;
  feeling: Mood;
  onboarded: boolean;
}

export const STYLE_VIBES = [
  "Soft & feminine",
  "Minimal & clean",
  "Classic & polished",
  "Cozy & relaxed",
  "Bold & expressive",
  "Modest & graceful",
  "Romantic",
  "Street & casual",
];
