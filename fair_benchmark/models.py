"""Data models for FAIR benchmark results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Finding:
    """A single FAIR check result, scoped to a collection and optionally an item."""

    principle: str  # e.g. "F1", "A1.1", "R1.3"
    collection_id: str  # e.g. "NOAA", "NDBC", "_platform" for platform-level
    item_id: str | None  # None for collection/platform-level findings
    grade: str  # A, B, C, D, F
    evidence: str
    gap: str = ""
    remediation: str = ""


@dataclass
class PrincipleScore:
    """Aggregated score for one FAIR principle across a scope (collection or platform)."""

    principle: str
    grade: str
    numeric: float  # 0-4 scale
    weight: float
    finding_count: int
    evidence_summary: str
    gap_summary: str
    remediation: str


@dataclass
class SourceScorecard:
    """FAIR scorecard for a single data source (collection)."""

    collection_id: str
    collection_title: str
    item_count: int
    principles: dict[str, PrincipleScore] = field(default_factory=dict)
    overall_grade: str = ""
    overall_numeric: float = 0.0
    weighted_numeric: float = 0.0


@dataclass
class PlatformScorecard:
    """FAIR scorecard for the entire AQUAVIEW platform."""

    principles: dict[str, PrincipleScore] = field(default_factory=dict)
    overall_grade: str = ""
    overall_numeric: float = 0.0
    weighted_numeric: float = 0.0
    source_scorecards: dict[str, SourceScorecard] = field(default_factory=dict)
    total_items: int = 0
    total_collections: int = 0


# Re-export CatalogSample from sampler to avoid circular imports
# (sampler imports config, models is standalone)
from .sampler import CatalogSample  # noqa: E402, F401

__all__ = [
    "Finding", "PrincipleScore", "SourceScorecard",
    "PlatformScorecard", "CatalogSample",
]
