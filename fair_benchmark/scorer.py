"""Scoring: aggregate findings into per-source and platform scorecards."""

from __future__ import annotations

from collections import defaultdict

from .config import GRADE_LABELS, GRADE_VALUES, PRINCIPLE_WEIGHTS
from .models import (
    CatalogSample,
    Finding,
    PlatformScorecard,
    PrincipleScore,
    SourceScorecard,
)


def score_findings(
    findings: list[Finding],
    sample: CatalogSample,
) -> PlatformScorecard:
    """Aggregate findings into per-source scorecards and a platform scorecard."""

    # Build collection title map
    coll_titles: dict[str, str] = {}
    for c in sample.collections:
        coll_titles[c.get("id", "")] = c.get("title", c.get("id", "unknown"))

    # Build collection item count map from collection_frequency
    coll_counts: dict[str, int] = {}
    for bucket in sample.collection_frequency:
        coll_counts[bucket.get("key", "")] = bucket.get("frequency", 0)

    # Group findings by collection_id
    by_collection: dict[str, list[Finding]] = defaultdict(list)
    platform_findings: list[Finding] = []

    for f in findings:
        if f.collection_id == "_platform":
            platform_findings.append(f)
        else:
            by_collection[f.collection_id].append(f)

    # Score each source
    source_scorecards: dict[str, SourceScorecard] = {}

    for coll_id, coll_findings in by_collection.items():
        sc = _build_scorecard(
            coll_findings,
            coll_id,
            coll_titles.get(coll_id, coll_id),
            coll_counts.get(coll_id, 0),
        )
        source_scorecards[coll_id] = sc

    # Build platform-level scorecard by merging platform findings + all source findings
    all_findings = platform_findings + findings  # platform findings take priority
    platform = _build_platform_scorecard(all_findings, source_scorecards, sample)

    return platform


def _build_scorecard(
    findings: list[Finding],
    coll_id: str,
    coll_title: str,
    item_count: int,
) -> SourceScorecard:
    """Build a scorecard for a single source."""
    sc = SourceScorecard(
        collection_id=coll_id,
        collection_title=coll_title,
        item_count=item_count,
    )

    # Group findings by principle
    by_principle: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_principle[f.principle].append(f)

    total_weighted = 0.0
    total_weight = 0.0

    for principle, p_findings in by_principle.items():
        ps = _aggregate_principle(principle, p_findings)
        sc.principles[principle] = ps
        total_weighted += ps.numeric * ps.weight
        total_weight += ps.weight

    if total_weight > 0:
        sc.weighted_numeric = total_weighted / total_weight
        sc.overall_numeric = sc.weighted_numeric
        sc.overall_grade = _numeric_to_grade(sc.weighted_numeric)

    return sc


def _build_platform_scorecard(
    all_findings: list[Finding],
    source_scorecards: dict[str, SourceScorecard],
    sample: CatalogSample,
) -> PlatformScorecard:
    """Build a platform-level scorecard from all findings."""
    platform = PlatformScorecard(
        source_scorecards=source_scorecards,
        total_items=sample.total_item_count or 0,
        total_collections=len(sample.collections),
    )

    # For each principle, compute the platform-level grade as the
    # weighted average of per-source grades (weighted by item count),
    # with platform-level findings as overrides for platform-only principles.
    by_principle: dict[str, list[Finding]] = defaultdict(list)
    for f in all_findings:
        by_principle[f.principle].append(f)

    total_weighted = 0.0
    total_weight = 0.0

    for principle in PRINCIPLE_WEIGHTS:
        p_findings = by_principle.get(principle, [])
        if p_findings:
            ps = _aggregate_principle(principle, p_findings)
        else:
            # No findings for this principle — mark as untested
            ps = PrincipleScore(
                principle=principle,
                grade="?",
                numeric=0,
                weight=PRINCIPLE_WEIGHTS[principle],
                finding_count=0,
                evidence_summary="Not tested — no findings",
                gap_summary="",
                remediation="",
            )
        platform.principles[principle] = ps
        if ps.finding_count > 0:
            total_weighted += ps.numeric * ps.weight
            total_weight += ps.weight

    if total_weight > 0:
        platform.weighted_numeric = total_weighted / total_weight
        platform.overall_numeric = platform.weighted_numeric
        platform.overall_grade = _numeric_to_grade(platform.weighted_numeric)

    return platform


def _aggregate_principle(principle: str, findings: list[Finding]) -> PrincipleScore:
    """Aggregate multiple findings for a single principle into one score."""
    if not findings:
        return PrincipleScore(
            principle=principle, grade="?", numeric=0,
            weight=PRINCIPLE_WEIGHTS.get(principle, 1.0),
            finding_count=0, evidence_summary="", gap_summary="", remediation="",
        )

    # Average the numeric grades
    numerics = [GRADE_VALUES.get(f.grade, 0) for f in findings]
    avg = sum(numerics) / len(numerics)

    # Collect unique gaps and remediations
    gaps = sorted({f.gap for f in findings if f.gap})
    remediations = sorted({f.remediation for f in findings if f.remediation})

    # Pick representative evidence (first few)
    evidence_samples = [f.evidence for f in findings[:3]]

    return PrincipleScore(
        principle=principle,
        grade=_numeric_to_grade(avg),
        numeric=round(avg, 2),
        weight=PRINCIPLE_WEIGHTS.get(principle, 1.0),
        finding_count=len(findings),
        evidence_summary="; ".join(evidence_samples),
        gap_summary="; ".join(gaps[:3]),
        remediation="; ".join(remediations[:3]),
    )


def _numeric_to_grade(numeric: float) -> str:
    """Convert numeric score (0-4) to letter grade."""
    if numeric >= 3.5:
        return "A"
    elif numeric >= 2.5:
        return "B"
    elif numeric >= 1.5:
        return "C"
    elif numeric >= 0.5:
        return "D"
    else:
        return "F"
