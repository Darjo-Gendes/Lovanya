# Local Image Generation — ComfyUI + Flux (GPU PC only)

Local, open-weight, **offline** image generation. No cloud, no API key — the
architecture-aligned alternative to "Nano Banana" (which is Google Gemini's
cloud model and cannot run locally). Consistent with
`architecture-decisions.md` (open-weight, self-hosted, free).

**Runs ONLY on the 8GB+ GPU PC.** The 940MX/2GB laptop cannot load these models.

## What it's for (and what it is NOT for)
- ✅ The optional **render stage** (`pipeline/app/render.py`): img2img from a
  SAM2 garment cutout → clean standardized product shot.
- ✅ One-off **build-time assets** (home-screen flower decor, placeholders).
- ❌ NOT for generating LookCards — those stay deterministic DOM rendering
  (`visual-pipeline-v1.md` rule #1). Do not route LookCards through a model.
- ❌ Do NOT add any cloud image API at runtime.

## Model choice — commercial-safe first, then VRAM
Lovanya ships as a product, so the weight LICENSE matters:
| Model | License | Verdict |
|---|---|---|
| **Flux.1 [schnell]** | Apache-2.0 | ✅ commercial OK, 4-step fast — preferred |
| **SDXL 1.0** | OpenRAIL-M | ✅ commercial OK, largest ecosystem, easiest 8GB fit |
| Flux.1 [dev] | non-commercial | ❌ do NOT use in the product |

Pick by actual VRAM (`nvidia-smi`):
- **8 GB:** SDXL fp16, or Flux schnell **GGUF Q4/Q5** (~6–7 GB). Launch ComfyUI
  with `--lowvram` if tight.
- **12 GB:** Flux schnell fp8 — comfortable.
- **16 GB+:** fp8 with headroom; co-residency (below) may become feasible.

## The one real gotcha: co-residency with the VLM
This card already hosts **Qwen3-VL-8B (NF4, ~5–6 GB)** + GroundingDINO + SAM2.
On 8 GB, Flux (~6–7 GB) and the VLM will **not** both stay resident. The
pipeline is already linear (`segment → analyze → render`), so render() runs
*after* analyze(): **free the VLM before invoking ComfyUI** (unload it, or run
ComfyUI as its own process and sequence the stages). Never hold both at once on
8 GB.

## Setup (the GPU-PC session pins exact commands to its CUDA/torch)
1. `git clone` ComfyUI; install into the existing GPU venv (torch already present).
2. Download the chosen weights into `ComfyUI/models/` (unet or checkpoint + VAE + CLIP).
3. Launch: `python main.py --lowvram` (8 GB) — exposes an HTTP API on `:8188`.
4. Smoke-test with one prompt via the `/prompt` API.

## Integration
- Replace the `render.py` stub with an HTTP call to the local ComfyUI API
  (img2img: cutout → clean product shot). Keep it **optional** and behind the
  same swappable posture as the rest of the pipeline; a failed/absent ComfyUI
  must degrade gracefully (skip the clean shot, keep the cutout).
- Optional: a ComfyUI MCP server (e.g. `artokun/comfyui-mcp`) so this machine's
  Claude Code can author/run workflows in natural language.

## Guardrails
- Local + open-weight only. No cloud image API at runtime.
- Commercial-safe weights only (schnell / SDXL — never Flux dev).
- One big model resident at a time on 8 GB.
