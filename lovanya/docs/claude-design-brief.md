# Loványa — design brief for Claude Design

Paste this whole file into claude.ai/design, then add one line saying which
screen you want (examples at the bottom). It tells the design agent Loványa's
look so the mockups come back on-brand instead of generic.

---

Design a mobile screen (390px wide phone frame) for **Loványa**, a premium AI
fashion companion app. Tagline: *"Your best friend in fashion."* It's warm,
elegant, feminine, calm, and emotionally supportive — never corporate or busy.
Think a luxury personal stylist living in your phone. Reference feel: Apple,
Airbnb, a quiet editorial fashion magazine.

## Color palette (use these exact values)
- Background (porcelain): `#fbf7f3`
- Card surface: `#fffdfb`
- Text ink (plum): `#46353f`; soft `#93808b`; faint `#b8a8b0`
- Primary accent (rosewood): `#b16c7c`; deep `#96525f`
- Blush (soft fills): `#f6e8e6`; deeper `#eed7d3`
- Champagne `#ede0cd` and gold `#c2a077` (warm accents)
- Sage `#a9b69b`; deep `#7e9070` (success / positive notes)
- Hairline borders: `#ede2dc`

Primary buttons: a soft gradient from rosewood `#b16c7c` to deep `#96525f`,
white text, fully rounded (pill). Secondary buttons: blush fill, rosewood text.

## Typography
- Display / headings: **Fraunces** (a soft serif), often *italic* for warmth —
  used for greetings, big numbers, and Aura's voice.
- UI / body: **Figtree** (clean sans).

## Shape & texture language
- Generous rounding: cards `~24px`, buttons fully pill, bottom sheets `~32px` top.
- Soft, low, warm shadows (never hard/gray): e.g. `0 18px 40px -20px rgb(70 53 63 / .22)`.
- Lots of breathing room, one idea per card, calm not dense.
- Subtle ambient background washes (faint rosewood/champagne/sage radial glows).
- Hairline `1px` borders in `#ede2dc` to separate, not heavy dividers.

## Aura (the companion)
Aura is the app's voice — a stylist best friend. She appears as a small
**luminous breathing orb** (a soft radial gradient sphere: pearl highlight →
champagne → rosewood `#b16c7c` → `#96525f`, with a gentle glow), NOT a cartoon
avatar or photo. Her messages sit in a card with a small "AURA" label and her
line in Fraunces italic. Tone: gentle, encouraging, specific, never judgmental
("Let's explore a softer combination" — never "those colors clash").

## Navigation
Floating pill bottom nav, 3 stops: **Today**, a center **Outfit Check** hero
button (rosewood gradient circle with a camera glyph, raised above the bar), and
**Closet**.

## Existing screens (for consistency)
- **Today:** date + "Good morning, [name]" greeting in Fraunces, an Aura message
  card, a weather card, a "What should I wear today?" hero with Style me / Outfit
  check buttons, and a soft stats row (pieces, styling moments, avg confidence).
- **Outfit Check:** photo → animated circular confidence score ring (rosewood→gold
  gradient), a breakdown of soft progress meters, "what's working" + one gentle
  suggestion, and an Aura note.
- **Closet:** rounded-square garment photos in a 3-col grid, pill filter chips,
  search field.
- **Style Me:** an outfit collage of items with a "why this works" explanation.

Keep new screens visually consistent with the above.
```

---

## Example prompts to append (pick one)
- "Design a **Style Journey** screen: a monthly progress view with a soft donut
  chart of how often outfits 'felt like me', a few stat bars (color harmony,
  versatility, confidence), and an encouraging Aura note."
- "Design an **Outfit Calendar** screen: what I wore each day this week as small
  outfit cards, with a gentle prompt to plan tomorrow."
- "Design a **Packing / Capsule** screen: pick an occasion + days, and Aura
  suggests a small capsule of pieces from my closet to bring."
- "Design a richer **Outfit Check result** screen variant with a before/after
  'try this instead' suggestion."
