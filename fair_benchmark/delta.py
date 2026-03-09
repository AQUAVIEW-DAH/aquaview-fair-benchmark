"""Delta comparison between benchmark runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import GRADE_VALUES


def find_previous_report(reports_dir: str | Path) -> Path | None:
    """Find the most recent JSON report in the reports directory."""
    reports_dir = Path(reports_dir)
    if not reports_dir.exists():
        return None

    json_files = sorted(reports_dir.glob("AQUAVIEW_FAIR_Assessment_*.json"), reverse=True)
    return json_files[0] if json_files else None


def load_previous(path: Path) -> dict[str, Any]:
    """Load a previous JSON report."""
    return json.loads(path.read_text())


def compute_delta(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> dict[str, Any]:
    """Compute the delta between two assessment JSON reports.

    Returns a dict with:
    - overall: {previous_grade, current_grade, change}
    - principles: {pid: {prev, curr, change}}
    - sources: {coll_id: {prev, curr, change}}
    - new_sources: [coll_ids added since last run]
    - removed_sources: [coll_ids no longer present]
    """
    delta: dict[str, Any] = {}

    # Overall
    prev_score = previous.get("overall_score", 0)
    curr_score = current.get("overall_score", 0)
    delta["overall"] = {
        "previous_grade": previous.get("overall_grade", "?"),
        "current_grade": current.get("overall_grade", "?"),
        "previous_score": prev_score,
        "current_score": curr_score,
        "change": round(curr_score - prev_score, 2),
    }

    # Per-principle
    delta["principles"] = {}
    prev_principles = previous.get("principles", {})
    curr_principles = current.get("principles", {})
    for pid in set(list(prev_principles.keys()) + list(curr_principles.keys())):
        prev_p = prev_principles.get(pid, {})
        curr_p = curr_principles.get(pid, {})
        delta["principles"][pid] = {
            "previous_grade": prev_p.get("grade", "?"),
            "current_grade": curr_p.get("grade", "?"),
            "previous_score": prev_p.get("score", 0),
            "current_score": curr_p.get("score", 0),
            "change": round(curr_p.get("score", 0) - prev_p.get("score", 0), 2),
        }

    # Per-source
    prev_sources = previous.get("sources", {})
    curr_sources = current.get("sources", {})
    all_source_ids = set(list(prev_sources.keys()) + list(curr_sources.keys()))

    delta["sources"] = {}
    delta["new_sources"] = []
    delta["removed_sources"] = []

    for coll_id in all_source_ids:
        if coll_id not in prev_sources:
            delta["new_sources"].append(coll_id)
            continue
        if coll_id not in curr_sources:
            delta["removed_sources"].append(coll_id)
            continue

        prev_s = prev_sources[coll_id]
        curr_s = curr_sources[coll_id]
        delta["sources"][coll_id] = {
            "previous_grade": prev_s.get("overall_grade", "?"),
            "current_grade": curr_s.get("overall_grade", "?"),
            "previous_score": prev_s.get("overall_score", 0),
            "current_score": curr_s.get("overall_score", 0),
            "change": round(
                curr_s.get("overall_score", 0) - prev_s.get("overall_score", 0), 2
            ),
        }

    return delta


def format_delta_markdown(delta: dict[str, Any]) -> str:
    """Format delta as Markdown section."""
    lines: list[str] = []

    overall = delta.get("overall", {})
    change = overall.get("change", 0)
    arrow = "^" if change > 0 else "v" if change < 0 else "="

    lines.append("## Delta from Previous Assessment")
    lines.append("")
    lines.append(
        f"**Overall:** {overall.get('previous_grade', '?')} "
        f"-> {overall.get('current_grade', '?')} "
        f"({change:+.2f}) {arrow}"
    )
    lines.append("")

    # Principle changes
    principles = delta.get("principles", {})
    changed = {k: v for k, v in principles.items() if v.get("change", 0) != 0}
    if changed:
        lines.append("### Principle Changes")
        lines.append("")
        lines.append("| Principle | Previous | Current | Change |")
        lines.append("|-----------|----------|---------|--------|")
        for pid in sorted(changed):
            p = changed[pid]
            c = p["change"]
            marker = "+" if c > 0 else ""
            lines.append(
                f"| {pid} | {p['previous_grade']} ({p['previous_score']:.2f}) | "
                f"{p['current_grade']} ({p['current_score']:.2f}) | {marker}{c:.2f} |"
            )
        lines.append("")
    else:
        lines.append("No principle scores changed.")
        lines.append("")

    # Source changes
    sources = delta.get("sources", {})
    source_changed = {k: v for k, v in sources.items() if v.get("change", 0) != 0}
    if source_changed:
        lines.append("### Source Changes")
        lines.append("")
        lines.append("| Source | Previous | Current | Change |")
        lines.append("|--------|----------|---------|--------|")
        for cid in sorted(source_changed, key=lambda x: source_changed[x]["change"], reverse=True):
            s = source_changed[cid]
            c = s["change"]
            marker = "+" if c > 0 else ""
            lines.append(
                f"| {cid} | {s['previous_grade']} ({s['previous_score']:.2f}) | "
                f"{s['current_grade']} ({s['current_score']:.2f}) | {marker}{c:.2f} |"
            )
        lines.append("")

    new = delta.get("new_sources", [])
    removed = delta.get("removed_sources", [])
    if new:
        lines.append(f"**New sources:** {', '.join(new)}")
        lines.append("")
    if removed:
        lines.append(f"**Removed sources:** {', '.join(removed)}")
        lines.append("")

    return "\n".join(lines)
