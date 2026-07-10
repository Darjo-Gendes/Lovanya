# Execution craft — numeric law (absorbed from vetted vendor skills)

Distilled 2026-07-09 from the vendor library (`ui-ux-pro-max` rules/data,
`fabricator` composition rules, `font-pairing` type mechanics). Their *choice
engines* — palette generators, font-pairing selectors, icon steering
(Phosphor/Lucide), theme dials — were **rejected**: those decisions are locked
in `tokens.md` and outrank anything here. This file is the craft floor every
implementation must clear; `tokens.md` says what things ARE, this says how
well they must be built.

## Accessibility floors (hard requirements)

- Text contrast ≥ 4.5:1 (large text ≥ 3:1; prefer ~7:1 for body on porcelain —
  ink `#48292E` on `#FAEDED` passes comfortably; watch muted `#A2908F` on
  blush surfaces).
- Touch targets ≥ 44×44pt with ≥ 8px between adjacent targets. Small glyphs
  get padding, never a bigger icon.
- Disabled = 0.38–0.5 opacity AND never color-only meaning. Focus state
  visible on every interactive element.
- Modal/sheet scrim 40–60% ink-tinted (rgba of `#48292E`), never pure black.

## Motion numbers (inside tokens.md's curves)

- Micro-interactions 150–300ms; complex transitions ≤ 400ms.
- Exit ≈ 60–70% of the enter duration. Stagger lists 30–50ms/item.
- Press scale .93–.97 (our existing values — keep).
- Animate `transform`/`opacity` only; never layout properties.

## Type mechanics (the faces are locked; this is the machinery)

- Reading text ≥ 14–16px with line-height 1.5–1.75. Metadata/eyebrows may run
  10–13px but must still pass contrast at that size.
- Measure 35–60 characters on mobile.
- New sizes snap to the ~1.25 ramp off 16 (12.8 / 16 / 20 / 25 / 31 / 39)
  before inventing bespoke values; the canonical mock's existing sizes win.
- `font-display: swap` + Latin subsetting always (the artifact build already
  complies — keep it that way).

## Composition rules

- **Radius nesting:** inner radius < outer, always (28px card → 18px photo →
  13px tile). Equal or larger inner radii read as broken.
- 4px spacing rhythm — round spacing to a multiple of 4 when in doubt.
- Rounded scroll containers require `overflow-hidden`.
- Form controls: `font-family: inherit` + consistent heights (36–44px) so
  toolbar/input rows align.
- **Contextual weight:** the same element in a denser context gets lighter —
  a badge sized for a card header is oversized inside a table row.
- **Format every number:** "183 pieces", "87 · Style Score", "12 wears" —
  never a bare integer without a unit or context word.
- z-index scale 0 / 10 / 20 / 40 / 100 — no arbitrary 9999s.

## Final audit (runs alongside the Critic on new/major UI)

- Every state styled? (hover, focus, disabled, empty, loading)
- Every number formatted?
- One hero + varied tile sizes — no row of four identical cards?
- Bars/charts fill their containers, endpoints emphasized?

## Vendor library note

Full machine-readable data (99 UX guidelines CSV, motion timing table, icon
concept-index) lives in `.claude/skills/_vendor/` — local reference,
gitignored. ⚠ The `app-design-manager` vendor skill is a repo-mutating GitHub
automation (`git push`, `gh pr create` on invocation) — never invoke it in
this repo.
