import type {
  Mood,
  Occasion,
  OutfitAnalysis,
  Profile,
  Recommendation,
  WardrobeItem,
  Weather,
  Category,
} from "@/lib/types";

/** A draft of a wardrobe item, produced by the AI from a photo. */
export interface ItemDraft {
  name: string;
  category: Category;
  colors: string[];
  warmth: 1 | 2 | 3;
  formality: 1 | 2 | 3;
  modest: boolean;
}

export interface RecContext {
  occasion: Occasion;
  mood: Mood;
  weather: Weather;
  modest: boolean;
  /** Preference memory: color-family -> bias weight (positive = loved). */
  bias: Record<string, number>;
  /** Item-pair keys the user has recently rejected. */
  rejectedPairs: string[];
}

/**
 * The single seam between Loványa and its intelligence.
 *
 * The MVP ships with MockStylist (lib/ai/mock.ts) — deterministic-ish,
 * color-aware, zero-cost. To go live, implement this interface against
 * Claude / OpenAI / Gemini vision in one new file and change one import
 * in lib/ai/index.ts. Nothing else in the app changes.
 */
export interface StylistAI {
  /** Analyze a worn outfit photo. `palette` is pre-extracted on-device. */
  analyzeOutfit(input: {
    palette: string[];
    occasion: Occasion;
    weather: Weather;
    profile: Profile;
  }): Promise<OutfitAnalysis>;

  /** Identify a single clothing item from its photo palette. */
  identifyItem(input: {
    palette: string[];
    modestDefault: boolean;
  }): Promise<ItemDraft>;

  /** Compose ranked complete outfits from the wardrobe. */
  recommendOutfits(input: {
    wardrobe: WardrobeItem[];
    context: RecContext;
  }): Promise<Recommendation[]>;
}
