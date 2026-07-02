# Loványa — Your Best Friend in Fashion

A premium AI fashion companion that helps you decide what to wear, organize
your wardrobe, and feel confident every day. Most fashion apps focus on
clothing; **Loványa focuses on confidence**.

> *"What should I wear today?" — answered in under 30 seconds.*

See [GOAL.md](./GOAL.md) for the definition of done.

---

## 1 · Product overview

| | |
|---|---|
| **Promise** | Answer "what should I wear?" in <30s, warmly |
| **Users** | Women 16–35, globally inclusive, modest-fashion aware |
| **Voice** | Aura — warm, gentle, encouraging; never judgmental |
| **Feel** | A luxury personal stylist inside your phone |
| **Stage** | MVP for the first 1,000 users — no backend, no accounts |

### The four pillars

1. **Outfit Intelligence** → *Outfit Check* — photo in, warm scored feedback out
2. **Wardrobe Memory** → *Closet* — photo in, organized item out (no manual tagging)
3. **Recommendation Engine** → *Style Me* — complete outfits from your own closet, with the *why*
4. **Aura** → ambient companion present on every screen (no chat tab — by design)

## 2 · MVP scope

**In:** onboarding (name/vibes/modesty/feeling) · Today dashboard · Outfit
Check (camera/upload → analysis) · Closet (AI add-item, search, filter, love,
delete) · Style Me (occasion/mood/weather-aware outfits + explanations +
accept/reject learning) · seeded demo closet · localStorage persistence ·
mocked weather · mock AI behind a swappable interface.

**Out (deliberately):** accounts, backend, real AI calls, social features,
shopping, push notifications, calendar, chat UI.

## 3 · Architecture

```
app/
  layout.tsx        fonts, metadata, AppShell
  page.tsx          Today (home)
  onboarding/       4-step warm intake
  check/            Outfit Check (capture → thinking → results)
  closet/           Wardrobe grid + Add/Detail sheets
  style-me/         Recommendations
components/
  AppShell, BottomNav, AuraOrb, AuraMessage, PhotoCapture,
  GarmentArt (SVG fallback for photoless items), ItemThumb, SettingsSheet,
  ui/ (Button, Chip, Sheet, ScoreRing, Meter)
lib/
  types.ts          domain model
  store.ts          zustand + persist (localStorage) + preference memory
  color.ts          palette extraction (canvas), naming, harmony scoring
  weather.ts        mocked deterministic weather
  seed.ts           capsule closet (80 real photos, sliced from the grid)
scripts/
  slice-wardrobe.ps1  one-time: slices the reference grid into per-item
                      square PNGs in public/wardrobe/ + samples their colors
  aura.ts           Aura's ambient copy
  ai/
    stylist.ts      StylistAI interface  ← the seam
    mock.ts         MockStylist (ships today)
    index.ts        export const stylist = MockStylist
```

### The AI seam (how to go live later)

Everything intelligent flows through one interface — `StylistAI` in
[lib/ai/stylist.ts](lib/ai/stylist.ts):

- `analyzeOutfit({palette, occasion, weather, profile})` → scored analysis
- `identifyItem({palette})` → categorized wardrobe item draft
- `recommendOutfits({wardrobe, context})` → ranked outfits with reasons

To use a real model: create `lib/ai/claude.ts` implementing the interface
(vision call via a Next.js route handler holding the API key) and change one
line in `lib/ai/index.ts`. No UI changes.

**The mock is honest where it can be:** palettes are *really* extracted from
the user's photos on-device (canvas sampling), color harmony is *really*
computed from hue relationships, and recommendations *really* respect
occasion, weather, modesty, and learned preferences. Only the language and
garment recognition are canned.

### Preference memory (criterion 5)

Stored in the zustand store, persisted to localStorage:

- **Love** an item → +1.5 bias to its color families, boosted in recs
- **"I'll wear this"** → +0.8 bias per family, wear count up (freshness model)
- **"Show me another"** → −0.25 bias + the exact combo is suppressed
- Aura references this learning in her explanations ("I leaned into the tones
  you've been loving lately")

## 4 · Key workflows

**Outfit Check** — open `/check` (camera starts immediately, upload fallback)
→ pick occasion chip (smart default: work on weekdays) → snap → on-device
palette extraction → `stylist.analyzeOutfit` → animated confidence ring,
4-dimension breakdown, what's working, one gentle thought, Aura's note → save
to journal.

**Add to closet** — `/closet` → + → photo → `stylist.identifyItem` → "Aura
sees" confirm card (correct category in one tap) → saved with real extracted
colors. Photos are downscaled to ≤512px JPEG to respect localStorage.

**Style Me** — `/style-me` → occasion + mood chips (weather automatic) →
`stylist.recommendOutfits` assembles dress- or top+bottom-based outfits,
layers for <19°, matches shoes/bag by harmony and formality, applies modesty
filter and preference bias → outfit collage + "why this works" + Aura's note
→ wear it (learns) or pass (also learns).

## 5 · Design system

- **Palette:** porcelain `#fbf7f3`, ink plum `#46353f`, rosewood `#b16c7c`,
  champagne/gold `#c2a077`, sage `#a9b69b`
- **Type:** Fraunces (display, italic for Aura's voice) + Figtree (UI)
- **Aura:** a breathing luminous orb — presence without a cartoon avatar
- **Nav:** floating pill, 3 stops — Today / **Outfit Check (hero)** / Closet
- **Stack:** Next.js 16 · React 19 · TypeScript · Tailwind v4 · zustand ·
  motion · lucide-react

## 6 · Run it

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production check
```

First run: 60-second onboarding, then a seeded capsule closet of 80 real
product photos so
Style Me works immediately. Settings (gear on Today) → restore demo closet /
start fresh.

## 7 · Roadmap after MVP

1. **Real vision** — implement `StylistAI` against Claude vision (route
   handler + API key), keep mock as offline fallback
2. **Real weather** — swap `lib/weather.ts` for Open-Meteo (keyless)
3. **Outfit journal & calendar** — the `checks` data already supports it
4. **Accounts & sync** — only when local-first stops being enough
5. **Personal Stylist subscription** — monetize Aura's deeper guidance
