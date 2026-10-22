"""Typed contracts shared by the analysis core, judge and API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["Poor", "Average", "Good", "Excellent"]
LABELS: list[str] = ["Poor", "Average", "Good", "Excellent"]
CriterionKey = Literal["rapport", "individual_attention", "energy", "homework_closure",
                       "presentation", "av_quality", "teaching_aids", "content_coverage"]


class Utterance(BaseModel):
    start: float
    end: float
    speaker: str          # anonymised: "Tutor" | "Student N" | "Unknown"
    role: Literal["tutor", "student", "unknown"]
    text: str


class Quote(BaseModel):
    t: float
    speaker: str
    quote: str


class Analysis(BaseModel):
    duration_s: float
    transcript_source: Literal["vtt", "txt", "asr", "none"]
    roles_estimated: bool = False
    features: dict[str, dict[str, float]] = Field(default_factory=dict)   # {"text": {...}, "audio": {...}, "visual": {...}}
    evidence: dict[str, list[Quote]] = Field(default_factory=dict)
    excerpt: str = ""
    content: dict = Field(default_factory=dict)       # subject, topics[], metrics (rater/content.py)
    evidence_windows: dict = Field(default_factory=dict)   # criterion -> top embedding-retrieved windows (rater/embeddings.py)
    warnings: list[str] = Field(default_factory=list)


class CriterionResult(BaseModel):
    score: int = Field(ge=1, le=5)
    rationale: str
    evidence: list[Quote] = Field(default_factory=list)


class Report(BaseModel):
    label: Label
    confidence: float = Field(ge=0, le=1)
    summary: str
    criteria: dict[str, CriterionResult]
    strengths: list[str]
    improvements: list[str]
    metrics: dict[str, float] = Field(default_factory=dict)
    judge: str
    content: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
