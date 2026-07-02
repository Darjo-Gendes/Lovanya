# Lovanya UI — Locked Design Signature

`Lovanya Home.dc.html` is the **canonical reference**. Every new screen must match it exactly. Copy its device frame, chrome, colors, type, and card system verbatim.

## Device frame (iPhone 17 Pro)
- Outer frame: `width:426px; height:898px; background:#1d1714; border-radius:56px; padding:12px;` shadow `0 60px 110px -36px rgba(170,110,120,.6), 0 0 0 1px rgba(255,255,255,.06) inset`
- Screen: `border-radius:46px; overflow:hidden; background:#FAEDED;` (≈402×874pt)
- Body bg behind frame: `#E8DADA`
- **Status bar**: absolute top, 54px tall, `color:#48292E`, "9:41" left (15px/600), signal+wifi+battery SVGs right. z-index 60.
- **Dynamic Island**: `top:11px; left:50%; translateX(-50%); width:120px; height:35px; background:#080606; border-radius:20px;` z-index 65.
- **Scroll area**: `position:absolute; inset:0; overflow-y:auto; padding:54px 0 132px;` — hide scrollbar (`.lvh-scroll` rules). Top pad clears status bar; bottom pad clears nav + home indicator.
- **Bottom nav**: fixed, `bottom:0; height:84px; background:#fff; border-radius:28px 28px 46px 46px;` shadow `0 -8px 26px -14px rgba(206,150,150,.45)`. 5 items (Home, Wardrobe, [center FAB], Journey, Profile), labels 11px. Center FAB: 54px circle, gradient `135deg,#E48EA0,#CE6C84`, 5px white border, margin-top:-30px.
- **Home indicator**: `bottom:8px; left:50%; translateX(-50%); width:135px; height:5px; border-radius:3px; background:rgba(72,41,46,.32);` z-index 66.

## Color tokens
- Pink primary `#D56F88` · deep accent `#CE6E86` / `#CE6C84`
- Primary button gradient `linear-gradient(135deg,#E48EA0,#CE6C84)`
- Soft card gradient `linear-gradient(155deg,#F8E1E1 0%,#F3D2D7 100%)`
- White cards `#fff`
- Headings `#48292E` / `#3E2A2E` · body `#6E5A5A` · muted `#A2908F` / `#A8968F`
- Icon chip tints: pink `#FBE0E2`, lilac `#EFE4F1`, sage `#E8F0D8`

## Type
- `Parisienne` → "Lovanya" logo wordmark only
- `Dancing Script` (600) → soft greeting line
- `Playfair Display` (600/700) → serif headings + big numbers
- `Poppins` (300–700) → all body, labels, UI. Eyebrow labels: 10px/600, letter-spacing 1.5px, color `#CE6E86`, UPPERCASE.

## Shape & shadow system
- Large feature card: `border-radius:28px`, shadow `0 18px 36px -20px rgba(206,140,150,.5)`
- Small card: `border-radius:18px`, shadow `0 12px 26px -18px rgba(206,150,150,.5)`
- Pill button: `border-radius:24px`, shadow `0 12px 22px -10px rgba(206,108,132,.7)`
- Icon chip: `border-radius:12–13px`, shadow `0 7px 16px -8px rgba(206,150,150,.6)`
- Sparkle motif (4-point star path) used as brand accent throughout.

## Imagery
- Real photos live in `assets/`. New imagery uses a styled placeholder (soft pink gradient + camera/image glyph + caption) until the user provides the real asset.
- Photos bleed off card edges with a `mask-image` linear fade.

## Output rules
- Standalone exports go in `standalone/<Name> (standalone).html` via super_inline_html. Keep the `<template id="__bundler_thumbnail">` in each .dc.html.
- Inline styles only (DC rules). One DC per screen.
