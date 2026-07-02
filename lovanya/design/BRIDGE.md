# Lovanya — Design ↔ Code Bridge

Two systems, one product. They are deliberately separate but **kept connected**;
when they disagree, we reconcile.

| System | Home | Owns | Source of truth for |
|---|---|---|---|
| **Claude Code** (this repo) | `lovanya/` | infrastructure, backend pipeline, the running app implementation | how the app is **built** |
| **Claude Design** ("Lovanya UI Design System") | claude.ai project `cc1989d8-…` | the visual/UI design (`*.dc.html` screens, Locked Signature) | how the app **looks** |

The canonical UI lives in Claude Design; the canonical implementation + backend
live here. Neither dictates the other's domain — they synchronize at the seam.

## The connection

The intended bridge is the **`DesignSync` MCP** (the `claude_design` server),
which reads/writes the design project natively. It needs design-system auth
(`/design-login`, or `/login` with a Claude subscription) — **not available in
the current environment**, so neither login command works here.

Active bridge = **browser RPC**. The user's browser is logged into claude.ai, so
from a tab on the project we call the design service directly:

- Endpoint base: `https://claude.ai/design/anthropic.omelette.api.v1alpha.OmeletteService/`
- `ListFiles` `{projectId}` → file list with `version` + `updatedAt` (drift signal)
- `GetFile` `{projectId, path}` → `{content (base64), contentType, version}`
- Headers: `Content-Type: application/json`, `Connect-Protocol-Version: 1`, `credentials: include`

Mirror of the live files: [`claude-ui/`](claude-ui). Drift baseline:
[`design-sync.json`](design-sync.json). See also the import procedure memory
note (`design-import-workflow`).

## Reconciliation policy

- **Design is the UI source of truth.** If a screen's design changes, the code
  follows. Pull the new `.dc.html`, then update the implementation to match.
- **Code/backend is built here.** The design does not specify backend; the
  pipeline + infrastructure are owned in this repo (see
  `claude-ui/uploads/files/architecture-decisions.md` for the intended backend).
- **On inconsistency or contingency → flag, don't silently pick a side.** Surface
  the diff to the user and let them choose which side wins, unless the policy
  above already settles it.

## Drift detection (design moved ahead of repo)

1. Browser tab on `https://claude.ai/design/p/cc1989d8-…`.
2. `ListFiles` → compare each file's `version` against `design-sync.json`.
3. Any changed/added/removed file = the design changed since last sync.
4. `GetFile` the changed files, strip the serve-time harness
   (`<script>`/`[data-omelette-injected]`) + URL query tokens, save into
   `claude-ui/`, and bump `design-sync.json`.
5. Then reconcile the affected screen implementation.

As of **2026-06-26** the repo mirror is **byte-identical** to the live project
(all 10 files) — fully in sync.

## Code-vs-design fidelity check (repo drifted from design)

On request, diff a built screen against its `.dc.html` (tokens, layout, copy,
type) and report mismatches. The Locked Signature (`claude-ui/CLAUDE.md`) is the
yardstick: device frame, color tokens, the 4-font type system (Parisienne /
Dancing Script / Playfair Display / Poppins), and the card/shadow system.

## Pushing back to the design (rare)

Writing changes **into** the design project is side-effectful and only done with
explicit user confirmation — natively via `DesignSync` once authorized, not via
the browser RPC by default.
