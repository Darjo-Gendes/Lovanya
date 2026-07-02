"""Typed contracts. Inputs are validated at the boundary (Pydantic v2).

The CANONICAL contract (Garment + Verdict) is the swappable-boundary shape from
framework/styling-framework.md — every analyzer (mock today, Qwen tomorrow)
returns the same structure, which is what makes the model swap a one-line change.
The App* models match lovanya/lib/types.ts so the frontend adapter stays thin.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["top", "bottom", "dress", "outerwear", "shoes", "bag", "accessory"]
Occasion = Literal["work", "class", "casual", "date", "event", "errands"]


# ---- API request boundary ----------------------------------------------------
class WeatherIn(BaseModel):
    tempC: float = 20.0
    condition: str = "cloudy"
    label: str = ""
    blurb: str = ""


class ProfileIn(BaseModel):
    name: str = "you"
    feeling: str = "confident"
    modest: bool = False


class AnalyzeRequest(BaseModel):
    palette: list[str] = Field(default_factory=list)
    occasion: Occasion = "casual"
    weather: WeatherIn = Field(default_factory=WeatherIn)
    profile: ProfileIn = Field(default_factory=ProfileIn)
    photo_base64: Optional[str] = None  # optional: server-side segment + extract


class IdentifyRequest(BaseModel):
    palette: list[str] = Field(default_factory=list)
    modestDefault: bool = True
    photo_base64: Optional[str] = None


# ---- App-facing responses (mirror lovanya/lib/types.ts) ----------------------
class Breakdown(BaseModel):
    label: str
    score: int
    note: str


class OutfitAnalysisOut(BaseModel):
    score: int
    headline: str
    palette: list[str]
    paletteNames: list[str]
    breakdown: list[Breakdown]
    whatWorks: list[str]
    gentleThought: str
    auraNote: str


class ItemDraftOut(BaseModel):
    name: str
    category: Category
    colors: list[str]
    warmth: int
    formality: int
    modest: bool


# ---- Canonical contract (swappable-boundary shape) ---------------------------
class Garment(BaseModel):
    category: Category = "top"
    subcategory: str = ""
    color_primary: str = ""
    color_secondary: str = ""
    pattern: str = "solid"
    formality: Literal["casual", "smart-casual", "business", "formal"] = "casual"
    fit: Literal["loose", "regular", "fitted"] = "regular"
    season: str = "all"
    notes: str = ""


class DimensionScores(BaseModel):
    color_harmony: int = 0
    elegance: int = 0
    outfit_cohesion: int = 0
    confidence_boost: int = 0
    consistency: int = 0
    style_growth: int = 0


class Verdict(BaseModel):
    dimension_scores: DimensionScores
    editorial_read: str
    elevate_suggestions: list[str]


class Analysis(BaseModel):
    garment: Garment
    verdict: Verdict


# ---- Internal analyzer step outputs ------------------------------------------
class Perception(BaseModel):
    """Perception step output — what the garment is."""

    category: Category = "top"
    colors: list[str] = Field(default_factory=list)
    warmth: int = 1
    formality: int = 2
    subcategory: str = ""


class Judgment(BaseModel):
    """Judgment step output — app-facing dims + on-brand language."""

    score: int
    headline: str
    harmony: int
    occasion_fit: int
    comfort: int
    cohesion: int
    what_works: list[str]
    gentle_thought: str
    aura_note: str
