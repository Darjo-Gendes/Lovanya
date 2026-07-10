<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Lovanya identity core (always in force)

Lovanya is not a wardrobe manager — she is a trusted fashion companion.
Warm before premium · elegant before trendy · personal before intelligent ·
inspiring before efficient · memorable before organized · calm before
feature-rich. If a change is more technically complete but less emotionally
resonant, it is wrong.

**For ANY UI/design work** (screens, components, flows, prototype, artifact):
load the `lovanya-design-director` skill FIRST (`.claude/skills/
lovanya-design-director/`) — gates before code, tokens before styles, and its
Critic exit-gate before any new/redesigned screen ships. When delegating UI
work to subagents, embed the relevant brief + token rules in the dispatch
prompt (subagents don't auto-load skills).

Language is editorial, never administrative ("Today's Look", never "Saved
Items"). Typography is locked (Parisienne = wordmark only · Dancing Script =
greetings · Playfair = headings · Poppins = UI). Icons: lucide-react (active =
heavier strokeWidth) + hand-drawn brand SVGs, which always outrank library
glyphs. (Iconsax deferred — 0.0.8 broke rendering; revisit with a mature
version only.) Single theme: rosewood on porcelain — no dark mode.
