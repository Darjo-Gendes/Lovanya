# Base vs. trained adapter — comparison (2026-07-05)

- **Base:** `Qwen/Qwen3-VL-8B-Instruct` (NF4), no adapter → `EVAL-REPORT-8b-base.md`
- **Trained:** same base + LoRA adapter `20260704-0928-epoch1` (120 gold
  examples, 1 epoch) → `EVAL-REPORT-adapter.md`

## Verdict: the trained adapter is a net improvement, with two known tradeoffs.

### Wins
- **Voice** — the clearest effect of training. Base is competent but
  formulaic ("creates a clean, classic contrast that works beautifully").
  The adapter picked up the gold set's warmer, wittier register: "the cream
  trousers are the anchor, the black top is the punctuation. You've got
  this." / "all the volume, all the ease."
- **Fix discipline** — cleaner add/swap suggestions; the base once drifted to
  "swap the shorts for a pair with embroidery detail" (modifying a garment),
  the adapter stayed on clean adds (belt, watch, sneakers).
- **Modesty** — respected by both; adapter phrases it well ("office-ready
  without looking like a uniform").

### Occasion discrimination — SURVIVED on clear mismatches
Ran three deliberate outfit/occasion mismatches (gold-scored 3-4):

| case | gold overall | adapter overall | adapter occasion_fit | redirect fix correct? |
|---|---|---|---|---|
| leopard cami + floral skirt → **wedding** | 3 | 5 | **3** | ✅ "swap crop top for satin blouse in ivory/champagne" |
| neon blazer + graphic tee + neon pants → **interview** | 3 | 5 | **4** | ✅ "swap purple pants for navy or gray" |
| neon colorblock + leopard pants → **belanja ke pasar** | 4 | 8 | 9 | ➖ called it fine (market is a forgiving occasion — defensible) |

The `occasion_fit` dimension correctly collapsed to 3-4 on the wedding and
interview cases, and the one-fix correctly steered toward formality. The
market case is genuinely borderline (a playful look for a market run is
arguably fine), so the model disagreeing with the gold label there is not a
clear failure.

### Tradeoffs
1. **Composite score compression.** The adapter pulls `overall` toward the
   middle-high — outliers land ~2 points above their gold labels (5 vs 3),
   and neutral good outfits cluster at 9/9/9/9 with less spread than base.
   The key `occasion_fit` signal still discriminates, but the headline number
   is more generous. Likely cause: the 110 non-outlier gold examples are
   mostly 9s, so 1 epoch over-weighted "nice → 9". A 2nd epoch (more passes
   over the 10 low-scored outliers) should sharpen this.
2. **Latency** — ~280s/judgment vs base ~195s (~45% slower): longer
   generations + PEFT wrapper overhead.

## Recommendation
Keep the epoch-1 adapter as the default judge (config `ADAPTER=auto` already
loads it) — the voice gain and retained occasion discrimination outweigh the
compressed composite score. To sharpen calibration, finish epoch 2 and/or
rebalance the gold set (more mid-range scores, more outliers) before the next
run.
