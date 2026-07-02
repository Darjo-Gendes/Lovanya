import type { OutfitAnalysis } from "@/lib/types";
import { MockStylist } from "./mock";
import type { ItemDraft, StylistAI } from "./stylist";

/**
 * Real StylistAI backed by the self-hosted pipeline service (pipeline/).
 *
 * Photo operations (analyze, identify) route to the pipeline; recommendation
 * stays local — it's pure deterministic logic over the wardrobe, no model. Any
 * pipeline failure falls back to MockStylist so the app keeps working when the
 * service is down. Wired in via index.ts when NEXT_PUBLIC_PIPELINE_URL is set.
 */
const BASE = (process.env.NEXT_PUBLIC_PIPELINE_URL ?? "").replace(/\/$/, "");

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`pipeline ${path} → ${res.status}`);
  return (await res.json()) as T;
}

export const PipelineStylist: StylistAI = {
  async analyzeOutfit(input) {
    try {
      return await post<OutfitAnalysis>("/analyze", input);
    } catch (err) {
      console.warn("[pipeline] analyzeOutfit fell back to mock:", err);
      return MockStylist.analyzeOutfit(input);
    }
  },

  async identifyItem(input) {
    try {
      return await post<ItemDraft>("/identify", {
        palette: input.palette,
        modestDefault: input.modestDefault,
      });
    } catch (err) {
      console.warn("[pipeline] identifyItem fell back to mock:", err);
      return MockStylist.identifyItem(input);
    }
  },

  // No model involved — keep the existing local recommender.
  recommendOutfits(input) {
    return MockStylist.recommendOutfits(input);
  },
};
