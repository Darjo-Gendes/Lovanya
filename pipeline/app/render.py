"""Stage 3 — optional clean product shot.

STUB. Real implementation (architecture-decisions.md): SDXL / Flux img2img turns
the isolated garment crop into a standardized, catalogue-style product shot for
the wardrobe entry. Optional by design — the pipeline is fully functional without
it, so the stub simply returns None.
"""
from __future__ import annotations

from typing import Optional


def render(crop: Optional[bytes]) -> Optional[bytes]:
    # TODO(real): SDXL/Flux img2img -> clean product shot bytes.
    return None
