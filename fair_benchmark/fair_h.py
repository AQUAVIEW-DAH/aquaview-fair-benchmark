"""FAIR-H: Human-experience scoring (v0 MVP).

Five lightweight heuristics that score the *human experience* of finding,
accessing, and reusing a dataset — distinct from FAIR-C's machine-token
presence checks. All metrics computable directly from STAC collection JSON.

The MVP intentionally trades nuance for simplicity: each metric is one
function returning (grade, numeric_score, evidence). Replace with smarter
implementations as the framework matures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

GRADE_LABELS = {4.0: "A", 3.0: "B", 2.0: "C", 1.0: "D", 0.0: "F"}


def _grade(score: float) -> str:
    if score >= 3.5:
        return "A"
    if score >= 2.5:
        return "B"
    if score >= 1.5:
        return "C"
    if score >= 0.5:
        return "D"
    return "F"


@dataclass
class HMetric:
    code: str
    name: str
    grade: str
    score: float
    evidence: str


# ---------- Findability-H ----------

LAY_TERMS = {
    "ocean", "sea", "water", "marine", "coastal", "coast",
    "temperature", "salinity", "current", "wave", "wind", "weather",
    "tide", "buoy", "glider", "satellite", "radar", "sonar",
    "fish", "biology", "chemistry", "oxygen", "chlorophyll",
    "gulf", "atlantic", "pacific", "arctic", "antarctic",
    "depth", "bathymetry", "elevation", "shore", "estuary",
}


def score_findability_h(coll: dict[str, Any]) -> HMetric:
    """F-H: Can a layperson find this with a plain-language search?

    Counts how many lay ocean/data terms appear in title+description+keywords.
    Higher term coverage = more human-discoverable via casual search.
    """
    title = (coll.get("title") or "").lower()
    desc = (coll.get("description") or "").lower()
    keywords = " ".join(coll.get("keywords", []) or []).lower()
    text = f"{title} {desc} {keywords}"

    matches = sum(1 for t in LAY_TERMS if t in text)
    if matches >= 6:
        score = 4.0
    elif matches >= 4:
        score = 3.0
    elif matches >= 2:
        score = 2.0
    elif matches >= 1:
        score = 1.0
    else:
        score = 0.0
    return HMetric(
        code="F-H",
        name="Findability (human)",
        grade=_grade(score),
        score=score,
        evidence=f"{matches} of {len(LAY_TERMS)} lay terms matched in title/description/keywords",
    )


# ---------- Accessibility-H1: format friction ----------

ANALYSIS_READY_FORMATS = {
    "application/x-zarr", "application/x-parquet", "application/parquet",
    "application/x-netcdf", "application/netcdf",
    "application/geo+json", "application/json",
    "image/tiff; application=geotiff", "image/tiff",
}
RAW_FORMATS = {"application/octet-stream", "application/x-binary", "text/plain"}


def score_format_friction_h(coll: dict[str, Any]) -> HMetric:
    """A-H1: How analysis-ready is the data format?

    A = analysis-ready (Zarr / Parquet / GeoTIFF / GeoJSON)
    B = structured but heavy (NetCDF, JSON)
    C = format declared but opaque (octet-stream, plain)
    D = no format info
    """
    item_assets = coll.get("item_assets", {}) or {}
    summaries = coll.get("summaries", {}) or {}
    types: list[str] = []
    for asset in item_assets.values():
        if isinstance(asset, dict) and asset.get("type"):
            types.append(asset["type"])
    if not types and "type" in summaries:
        types = summaries.get("type") or []

    if not types:
        return HMetric("A-H1", "Format friction", "D", 1.0, "No asset types declared")

    has_ar = any(t in ANALYSIS_READY_FORMATS for t in types)
    has_raw = any(t in RAW_FORMATS for t in types)

    if has_ar and not has_raw:
        score, ev = 4.0, f"Analysis-ready formats: {', '.join(set(types))[:80]}"
    elif has_ar:
        score, ev = 3.0, f"Mixed formats including analysis-ready: {', '.join(set(types))[:80]}"
    elif has_raw:
        score, ev = 2.0, f"Opaque/raw formats: {', '.join(set(types))[:80]}"
    else:
        score, ev = 3.0, f"Structured but heavy: {', '.join(set(types))[:80]}"
    return HMetric("A-H1", "Format friction", _grade(score), score, ev)


# ---------- Accessibility-H2: access friction ----------

def score_access_friction_h(coll: dict[str, Any]) -> HMetric:
    """A-H2: Can a human download without auth/forms?

    A = direct HTTPS to data
    B = portal with public download
    C = registration / form required
    D = restricted / unclear
    """
    links = coll.get("links", []) or []
    has_data_link = any(
        link.get("rel") in ("data", "items", "self") and link.get("href", "").startswith("https://")
        for link in links
    )
    desc = (coll.get("description") or "").lower()
    requires_auth = any(
        s in desc for s in ["login required", "registration required", "credentials", "api key required", "authenticated"]
    )

    if requires_auth:
        score, ev = 2.0, "Description mentions auth/registration required"
    elif has_data_link:
        score, ev = 4.0, "Direct HTTPS data links present"
    else:
        score, ev = 3.0, "Portal-mediated access (no direct data link found)"
    return HMetric("A-H2", "Access friction", _grade(score), score, ev)


# ---------- Reusability-H1: license clarity ----------

KNOWN_HUMAN_LICENSES = {
    "cc-by", "cc-by-4.0", "cc-by-sa", "cc0", "cc-0",
    "mit", "apache-2.0", "bsd",
    "public domain", "publicdomain",
}


def score_license_clarity_h(coll: dict[str, Any]) -> HMetric:
    """R-H1: Is the license stated in human-readable form?

    A = recognizable open license string ("CC-BY", "Public Domain", etc.)
    B = license URL only (machine but not human-friendly)
    C = vague text ("free for use", "contact us")
    D = no license
    """
    lic = coll.get("license") or ""
    lic_lower = lic.lower()
    if not lic:
        return HMetric("R-H1", "License clarity", "D", 1.0, "No license field")
    if lic_lower in KNOWN_HUMAN_LICENSES or any(k in lic_lower for k in KNOWN_HUMAN_LICENSES):
        return HMetric("R-H1", "License clarity", "A", 4.0, f"Human-readable license: {lic}")
    if lic_lower.startswith("http"):
        return HMetric("R-H1", "License clarity", "B", 3.0, f"License URL only: {lic[:60]}")
    if lic_lower in ("various", "proprietary", "see description"):
        return HMetric("R-H1", "License clarity", "C", 2.0, f"Vague: {lic}")
    return HMetric("R-H1", "License clarity", "C", 2.0, f"Non-standard: {lic[:40]}")


# ---------- Reusability-H2: narrative documentation ----------

def score_narrative_docs_h(coll: dict[str, Any]) -> HMetric:
    """R-H2: Is there narrative documentation a human can read?

    A = rich description (>500 chars) + provider info + usage hint
    B = decent description (>200 chars) + provider info
    C = short description (<200 chars) or no providers
    D = no description
    """
    desc = coll.get("description") or ""
    providers = coll.get("providers", []) or []
    desc_len = len(desc)
    has_providers = bool(providers)

    if desc_len > 500 and has_providers:
        return HMetric("R-H2", "Narrative docs", "A", 4.0,
                       f"{desc_len}-char description, {len(providers)} provider(s)")
    if desc_len > 200 and has_providers:
        return HMetric("R-H2", "Narrative docs", "B", 3.0,
                       f"{desc_len}-char description, {len(providers)} provider(s)")
    if desc_len > 0:
        return HMetric("R-H2", "Narrative docs", "C", 2.0,
                       f"{desc_len}-char description, providers={'yes' if has_providers else 'no'}")
    return HMetric("R-H2", "Narrative docs", "D", 1.0, "No description")


# ---------- Composite ----------

@dataclass
class FairHScorecard:
    collection_id: str
    metrics: list[HMetric]
    overall_grade: str
    overall_score: float


def score_fair_h(coll: dict[str, Any]) -> FairHScorecard:
    """Run all FAIR-H metrics on a STAC collection dict."""
    metrics = [
        score_findability_h(coll),
        score_format_friction_h(coll),
        score_access_friction_h(coll),
        score_license_clarity_h(coll),
        score_narrative_docs_h(coll),
    ]
    overall = sum(m.score for m in metrics) / len(metrics)
    return FairHScorecard(
        collection_id=coll.get("id", "unknown"),
        metrics=metrics,
        overall_grade=_grade(overall),
        overall_score=overall,
    )
