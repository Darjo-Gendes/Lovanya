# Lovanya — Concrete Design Law (the binding layer)

Philosophy lives in SKILL.md; this file is what makes output *Lovanya* and
not merely pretty. Canonical visual reference: `lovanya/public/prototype/
lovanya-app.html` (single-file app) and `lovanya/design/claude-ui/CLAUDE.md`
(device-frame spec). App tokens: `lovanya/app/globals.css` (@theme).

## Color

- Rosewood primary `#D56F88` · deep `#C25C76` / `#CE6C84` · eyebrow `#CE6E86`
- Surface porcelain `#FAEDED` · cards `#FFFFFF` · line `#EFD9DC`
- Ink `#48292E` · body `#6E5A5A` · muted/faint `#A2908F`/`#A8968F`
- Blush `#FBEBEB` / `#F6DCDE` · champagne `#F4E7D6` · gold `#C79A4A`/`#E8B24A`
  · sage `#8DA767` on `#E8F0D8` · lilac tint `#EFE4F1`
- Primary button gradient `linear-gradient(135deg,#E48EA0,#CE6C84)`
- Soft feature-card gradient `linear-gradient(155deg,#F8E1E1,#F3D2D7)`
- Tailwind tokens exist for most of these (`rosewood`, `porcelain`, `blush`,
  `ink`, `line`, `sage`, `gold`…) — use tokens, not raw hex, in app code.
- Single-theme by design: rosewood-on-porcelain IS the identity. No dark mode.

## Typography (locked — enforce, never explore)

- **Parisienne** → the "Lovanya" wordmark ONLY. Never body, never headings.
- **Dancing Script 600/700** → soft greeting lines ("Good morning,").
- **Playfair Display 500–700** (`font-display`) → serif headings, look titles,
  big numbers, verdict lines.
- **Poppins 300–700** → all UI: body, labels, buttons, meta.
- Emotional hierarchy on every screen: large serif title → soft descriptor →
  quiet metadata. Text never competes at equal weight.
- Eyebrow labels: 10px/600, letter-spacing 1.5px, uppercase, `#CE6E86`.

## Icon law (lucide current; Iconsax deferred 2026-07-10)

- **lucide-react** is the app's utility icon language. Active state = heavier
  `strokeWidth` (≈1.8 resting / 2.2 active). Sizes on a 16/20/24 grid; color
  inherits `currentColor` from `text-*` tokens.
- **Iconsax was trialed and reverted (2026-07-10):** `iconsax-react@0.0.8` is
  too immature — missing common glyphs (no leaf/apparel/wine) and its icons
  don't inherit `currentColor`, so white-on-pink/rosewood elements rendered in
  its default gray → broke every icon. Revisit ONLY with a mature Iconsax
  package that fixes both; until then, do not reintroduce it.
- **Hand-drawn brand SVGs stay** and outrank Iconsax: the 4-point sparkle
  motif, hangers, hearts, flower deco — these ARE brand warmth. Never replace
  them with library glyphs; never mix a third icon set.
- The prototype keeps its hand-drawn inline SVGs (it is the canonical mock).

## Shape & shadow system

- Feature card `28px` radius, shadow `0 18px 36px -20px rgba(206,140,150,.5)`
- Standard card `20–26px`, `0 18px 36px -22px rgba(206,140,150,.5)`
- Small card/tile `13–18px`, `0 12px 26px -18px rgba(206,150,150,.5)`
- Pill buttons `24px`, lift shadow `0 12px 22px -10px rgba(206,108,132,.7)`
- Icon tile `13px`, `0 7px 16px -8px rgba(206,150,150,.6)` on white
- Photos bleed off card edges with `mask-image` linear fades.

## Layout & motion

- Mobile-first, 430px max shell, generous 20–24px gutters (`px-5` shell).
- Screen-enter: fade+8px rise, ~0.3s `cubic-bezier(.32,.72,.3,1)`. Bars/rings
  animate in with ~1s eased fills. Press states scale .93–.97.
- Horizontal rows are always `overflow-x-auto no-scrollbar -mx-5 px-5`.
- **Gotcha (React 19 + motion):** AnimatePresence exit animations never
  complete in this app. Unmount with conditional rendering; entrance
  animations only.

## Component idioms (reuse, don't reinvent)

`Sheet` (bottom sheet) · `Chip` (selected = rosewood gradient) · `Button`
(default gradient / `soft` white) · `Meter` (scored bars) · `ItemThumb`
(photo → art → swatch fallback) · `LookCard` (deterministic collage) ·
score badge = rosewood→gold gradient circle with white Playfair numeral.

## Copy micro-rules

Apostrophes in JSX as `&rsquo;`. Dates "Jun 20, 2026" (or "Today"/
"Yesterday"). Occasion labels from `OCCASIONS`, never raw ids. Scores shown
with warmth ("87 · Style Score"), never bare grades.
