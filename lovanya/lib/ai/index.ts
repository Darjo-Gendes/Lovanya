import type { StylistAI } from "./stylist";
import { MockStylist } from "./mock";
import { PipelineStylist } from "./pipeline";

/**
 * The single seam between Loványa and its intelligence.
 * Uses the self-hosted pipeline (../../pipeline) when NEXT_PUBLIC_PIPELINE_URL
 * is set, otherwise the zero-cost local mock. The pipeline adapter itself falls
 * back to the mock on any error, so the app never breaks if the service is down.
 */
export const stylist: StylistAI = process.env.NEXT_PUBLIC_PIPELINE_URL
  ? PipelineStylist
  : MockStylist;

export type { StylistAI, ItemDraft, RecContext } from "./stylist";
export { pairKey } from "./mock";
