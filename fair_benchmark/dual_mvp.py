"""Generate a FAIR-C / FAIR-H dual-score MVP report (HTML).

Picks a handful of representative AQUAVIEW collections, scores them on both
FAIR-C (existing benchmark JSON) and FAIR-H (new heuristics), and renders a
side-by-side HTML report including a UI mockup of how the scores would
appear on an AQUAVIEW dataset page.

Run:
    python -m fair_benchmark.dual_mvp [--report PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from urllib.request import urlopen

from .fair_h import FairHScorecard, HMetric, score_fair_h

SFEOS_BASE = "https://aquaview-sfeos-1025757962819.us-east1.run.app"
DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / "AQUAVIEW_FAIR_Assessment_2026-03-09.json"
)
DEFAULT_OUT = (
    Path(__file__).resolve().parents[1]
    / "reports"
    / f"AQUAVIEW_FAIR_Dual_{date.today()}.html"
)

# Pick collections spanning the FAIR-C leaderboard. Hand-picked from the
# 38-source baseline: a few high (B, ~3.0), middle (~2.6), and low (~2.4).
SELECTED_SOURCE_KEYS = [
    "AOOS",        # Top tier — IOOS regional, well-curated
    "WOD",         # Largest catalog, NCEI-curated
    "NDBC",        # NOAA Buoys — household name
    "DIGITALCOAST",
    "sentinel-2-l2a",  # Satellite
    "INCIDENT_NEWS",   # Lower tier
    "NOS_COOPS",       # Lowest (C grade in baseline)
]


def fetch_collection(collection_id: str) -> dict | None:
    url = f"{SFEOS_BASE}/collections/{collection_id}"
    try:
        with urlopen(url, timeout=15) as resp:
            return json.load(resp)
    except Exception as e:
        print(f"  warn: could not fetch {collection_id}: {e}", file=sys.stderr)
        return None


# Five parallel categories, mapping FAIR-C principles to FAIR-H metrics so the
# side-by-side reads as one row per category rather than two unrelated tables.
PARALLEL_CATEGORIES = [
    ("Findable",            "F4",   "F-H"),
    ("Format-accessible",   "A1",   "A-H1"),
    ("Auth-accessible",     "A1.2", "A-H2"),
    ("Licensed for reuse",  "R1.1", "R-H1"),
    ("Documented for reuse","R1",   "R-H2"),
]


def fair_c_summary(report: dict, source_key: str) -> dict | None:
    """Pull the FAIR-C summary for one source, falling back to platform-level
    scores for any of the 5 canonical principles missing from the source data
    (so every dataset card renders all 5 rows consistently)."""
    sources = report.get("sources", {}) or report.get("source_scorecards", {})
    platform_principles = report.get("principles", {}) or {}
    for key in (source_key, source_key.upper(), source_key.lower()):
        if key in sources:
            sc = sources[key]
            principles = dict(sc.get("principles", {}))
            # Fill missing parallel-category principles from platform fallback
            for _, c_code, _ in PARALLEL_CATEGORIES:
                if c_code not in principles and c_code in platform_principles:
                    p = dict(platform_principles[c_code])
                    p["_fallback"] = True
                    principles[c_code] = p
            return {
                "id": key,
                "title": sc.get("title") or sc.get("collection_title", key),
                "items": sc.get("item_count", 0),
                "grade": sc.get("overall_grade", "?"),
                "score": sc.get("overall_score", 0.0),
                "principles": principles,
            }
    return None


GRADE_COLORS = {
    "A": "#16a34a", "B": "#65a30d", "C": "#ca8a04", "D": "#dc2626", "F": "#7f1d1d",
}


def render_score_pill(grade: str, score: float) -> str:
    color = GRADE_COLORS.get(grade, "#64748b")
    return (
        f'<span style="display:inline-block;background:{color};color:white;'
        f'border-radius:6px;padding:2px 10px;font-weight:600;font-family:system-ui;'
        f'font-size:14px;letter-spacing:.02em;">{grade} · {score:.2f}</span>'
    )


def render_metric_row(label: str, code: str, grade: str, score: float, evidence: str) -> str:
    color = GRADE_COLORS.get(grade, "#64748b")
    return f"""<tr>
        <td style="padding:6px 12px 6px 0;color:#64748b;font-size:12px;font-family:ui-monospace,monospace;">{code}</td>
        <td style="padding:6px 12px 6px 0;font-size:13px;">{label}</td>
        <td style="padding:6px 0;text-align:right;"><span style="color:{color};font-weight:600;">{grade}</span> <span style="color:#94a3b8;font-size:12px;">({score:.2f})</span></td>
        <td style="padding:6px 0 6px 12px;color:#64748b;font-size:12px;">{evidence}</td>
    </tr>"""


def _h_metric_by_code(h_card: FairHScorecard, code: str) -> HMetric | None:
    for m in h_card.metrics:
        if m.code == code:
            return m
    return None


def render_parallel_row(label: str, c_code: str, h_code: str, c_summary: dict, h_card: FairHScorecard) -> str:
    """One row showing FAIR-C + FAIR-H scores for the same category, side-by-side."""
    c = c_summary["principles"].get(c_code, {})
    c_grade = c.get("grade", "—")
    c_score = c.get("score", c.get("numeric"))
    c_score_str = f"{c_score:.2f}" if isinstance(c_score, (int, float)) else "—"
    c_color = GRADE_COLORS.get(c_grade, "#cbd5e1")
    c_fallback = c.get("_fallback")

    h = _h_metric_by_code(h_card, h_code)
    if h:
        h_grade = h.grade
        h_score_str = f"{h.score:.2f}"
        h_color = GRADE_COLORS.get(h_grade, "#cbd5e1")
        h_evidence = h.evidence
    else:
        h_grade = "—"
        h_score_str = "—"
        h_color = "#cbd5e1"
        h_evidence = ""

    delta = ""
    if isinstance(c_score, (int, float)) and h:
        d = h.score - c_score
        if abs(d) >= 0.5:
            arrow = "↑" if d > 0 else "↓"
            delta = f'<span style="color:#94a3b8;font-size:11px;margin-left:6px;">{arrow}{abs(d):.1f}</span>'

    fb_marker = '<span title="platform-level fallback" style="color:#cbd5e1;font-size:10px;margin-left:4px;">·</span>' if c_fallback else ""

    return f"""<tr style="border-top:1px solid #f1f5f9;">
        <td style="padding:10px 0;font-size:13px;color:#0f172a;font-weight:500;">{label}</td>
        <td style="padding:10px 12px;text-align:right;width:130px;">
            <span style="font-family:ui-monospace,monospace;font-size:11px;color:#94a3b8;">{c_code}{fb_marker}</span>
            <span style="color:{c_color};font-weight:700;margin-left:8px;">{c_grade}</span>
            <span style="color:#94a3b8;font-size:12px;margin-left:4px;">{c_score_str}</span>
        </td>
        <td style="padding:10px 12px;text-align:right;width:140px;">
            <span style="font-family:ui-monospace,monospace;font-size:11px;color:#94a3b8;">{h_code}</span>
            <span style="color:{h_color};font-weight:700;margin-left:8px;">{h_grade}</span>
            <span style="color:#94a3b8;font-size:12px;margin-left:4px;">{h_score_str}</span>
            {delta}
        </td>
        <td style="padding:10px 0 10px 12px;color:#64748b;font-size:12px;">{h_evidence[:70]}</td>
    </tr>"""


def render_dataset_card(c_summary: dict, h_card: FairHScorecard, full_coll: dict) -> str:
    title = full_coll.get("title") or c_summary["title"]
    desc = (full_coll.get("description") or "")[:280]
    items = c_summary["items"]

    c_pill = render_score_pill(c_summary["grade"], c_summary["score"])
    h_pill = render_score_pill(h_card.overall_grade, h_card.overall_score)

    rows = "".join(
        render_parallel_row(label, c_code, h_code, c_summary, h_card)
        for label, c_code, h_code in PARALLEL_CATEGORIES
    )

    return f"""
<section style="border:1px solid #e2e8f0;border-radius:12px;padding:24px;margin-bottom:24px;background:white;">
    <div style="display:flex;justify-content:space-between;align-items:start;gap:16px;margin-bottom:8px;">
        <div style="flex:1;">
            <h3 style="margin:0;font-size:18px;color:#0f172a;">{title}</h3>
            <div style="color:#64748b;font-size:13px;margin-top:4px;">{c_summary['id']} · {items:,} items</div>
        </div>
        <div style="display:flex;gap:10px;align-items:center;">
            <span style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;">FAIR-C</span>{c_pill}
            <span style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin-left:8px;">FAIR-H</span>{h_pill}
        </div>
    </div>
    <p style="color:#475569;font-size:13px;line-height:1.5;margin:8px 0 16px 0;">{desc}{'…' if len(desc) >= 280 else ''}</p>
    <table style="width:100%;border-collapse:collapse;">
        <thead>
            <tr style="border-bottom:2px solid #e2e8f0;">
                <th style="padding:8px 0;text-align:left;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">Category</th>
                <th style="padding:8px 12px;text-align:right;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">FAIR-C</th>
                <th style="padding:8px 12px;text-align:right;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">FAIR-H</th>
                <th style="padding:8px 0 8px 12px;text-align:left;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">FAIR-H evidence</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
</section>"""


def _principle_label(code: str) -> str:
    return {
        "F1": "Persistent identifier",
        "F2": "Rich metadata",
        "F3": "ID in metadata",
        "F4": "Indexed/searchable",
        "I1": "Formal language",
        "I2": "FAIR vocabularies",
        "I3": "Qualified references",
        "R1": "Rich description",
        "R1.1": "License",
        "R1.2": "Provenance",
        "R1.3": "Community standards",
        "A1": "Protocol",
        "A1.1": "Open protocol",
        "A1.2": "Auth/authz",
        "A2": "Metadata persistence",
    }.get(code, code)


# ---------- UI mockup of an AQUAVIEW dataset detail page ----------

def render_ui_mockup(c_summary: dict, h_card: FairHScorecard, full_coll: dict) -> str:
    """Mockup styled as the FAIR tab on an aquaview.org dataset detail page —
    same chrome (breadcrumb → title → tab bar → tab body) so it's clear where
    this would live."""
    title = full_coll.get("title") or c_summary["title"]
    desc = (full_coll.get("description") or "")[:200]
    c_pill = render_score_pill(c_summary["grade"], c_summary["score"])
    h_pill = render_score_pill(h_card.overall_grade, h_card.overall_score)

    # Same parallel-row table inside the tab content
    rows = "".join(
        render_parallel_row(label, c_code, h_code, c_summary, h_card)
        for label, c_code, h_code in PARALLEL_CATEGORIES
    )

    # Tab bar — FAIR active
    tabs_html = ""
    for name in ("Overview", "Preview", "Statistics", "FAIR", "Data", "Metadata"):
        active = name == "FAIR"
        style = (
            "padding:10px 16px;font-size:13px;font-weight:600;color:#0f172a;"
            "border-bottom:2px solid #0ea5e9;"
            if active
            else "padding:10px 16px;font-size:13px;color:#64748b;border-bottom:2px solid transparent;"
        )
        tabs_html += f'<div style="{style}cursor:pointer;">{name}</div>'

    return f"""
<div style="background:#f8fafc;padding:24px;border-radius:12px;margin-top:24px;border:1px dashed #cbd5e1;">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;margin-bottom:12px;">
        UI mockup — FAIR tab on /explore/item/{c_summary['id']}/&lt;item-id&gt;
    </div>
    <!-- Page chrome -->
    <div style="background:white;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,0.05);overflow:hidden;">
        <div style="padding:20px 24px 0 24px;">
            <div style="font-size:13px;color:#64748b;margin-bottom:6px;">explore / {c_summary['id']} / &lt;item-id&gt;</div>
            <h2 style="margin:4px 0 4px 0;font-size:22px;color:#0f172a;letter-spacing:-0.01em;">{title}</h2>
            <p style="color:#475569;font-size:13px;line-height:1.5;margin:6px 0 16px 0;">{desc}{'…' if len(desc) >= 200 else ''}</p>
        </div>
        <!-- Tab bar -->
        <div style="display:flex;gap:0;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;background:#fafbfc;padding:0 24px;">
            {tabs_html}
        </div>
        <!-- Tab content -->
        <div style="padding:24px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <div>
                    <h3 style="margin:0;font-size:15px;color:#0f172a;">FAIR Score — dual framework</h3>
                    <div style="color:#94a3b8;font-size:12px;margin-top:2px;">Machine-actionability (FAIR-C) and human-experience (FAIR-H), measured separately on the same dataset.</div>
                </div>
                <div style="display:flex;gap:10px;align-items:center;">
                    <span style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;">FAIR-C</span>{c_pill}
                    <span style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;margin-left:8px;">FAIR-H</span>{h_pill}
                </div>
            </div>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="border-bottom:2px solid #e2e8f0;">
                        <th style="padding:8px 0;text-align:left;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">Category</th>
                        <th style="padding:8px 12px;text-align:right;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">FAIR-C</th>
                        <th style="padding:8px 12px;text-align:right;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">FAIR-H</th>
                        <th style="padding:8px 0 8px 12px;text-align:left;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em;font-weight:600;">Evidence</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <div style="margin-top:16px;padding:12px 16px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:4px;font-size:12px;color:#0c4a6e;">
                <strong>What's new:</strong> FAIR-H surfaces the human experience (lay-keyword discoverability, format friction, license clarity, narrative docs) — orthogonal to FAIR-C's machine-token presence. Where the two scores diverge is where the platform owes its users a closer look.
            </div>
        </div>
    </div>
</div>"""


# ---------- Main ----------

def render_html(rows: list[tuple[dict, FairHScorecard, dict]], baseline_date: str) -> str:
    cards = "\n".join(render_dataset_card(c, h, f) for c, h, f in rows)
    # Pick the most-divergent dataset for the UI mockup
    if rows:
        rows_sorted = sorted(rows, key=lambda r: abs(r[0]["score"] - r[1].overall_score), reverse=True)
        c_top, h_top, full_top = rows_sorted[0]
        mockup = render_ui_mockup(c_top, h_top, full_top)
    else:
        mockup = "<p>No data.</p>"

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>AQUAVIEW FAIR Dual-Score MVP — {date.today()}</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #f1f5f9; color: #0f172a; max-width: 1100px; margin: 32px auto; padding: 0 24px; line-height: 1.5; }}
  h1 {{ font-size: 28px; margin-bottom: 6px; }}
  .lede {{ color: #475569; font-size: 16px; margin-bottom: 32px; }}
  .kicker {{ font-size: 12px; text-transform: uppercase; letter-spacing: .1em; color: #64748b; margin-bottom: 4px; }}
  details {{ margin: 16px 0; }}
  summary {{ cursor: pointer; font-weight: 600; color: #0f172a; }}
</style>
</head><body>
<div class="kicker">v0 MVP · {date.today()}</div>
<h1>AQUAVIEW FAIR — Dual-Score Demo</h1>
<p class="lede">A side-by-side measurement of <strong>FAIR-C</strong> (machine-actionability, computed by the existing benchmark) and <strong>FAIR-H</strong> (human-experience, new lightweight heuristics). The premise: machine-FAIR and human-FAIR diverge, and a real platform owes its users both views. Baseline FAIR-C from {baseline_date}; FAIR-H computed live.</p>

<details>
<summary>About the FAIR-H v0 metrics</summary>
<ul style="color:#475569;font-size:14px;">
<li><strong>F-H Findability</strong> — count of plain-language ocean/data terms in title/description/keywords</li>
<li><strong>A-H1 Format friction</strong> — analysis-ready (Zarr/Parquet/GeoTIFF) vs heavy (NetCDF) vs opaque</li>
<li><strong>A-H2 Access friction</strong> — direct HTTPS vs auth-required</li>
<li><strong>R-H1 License clarity</strong> — human-readable string vs URL-only vs missing</li>
<li><strong>R-H2 Narrative docs</strong> — description length × provider info</li>
</ul>
<p style="color:#475569;font-size:13px;">All metrics intentionally simple for v0. Future versions plug in TF-IDF discoverability, Claude-judged narrative quality, and Warren Wood's NRL framework primitives.</p>
</details>

<h2 style="margin-top:32px;">Side-by-side scoring — selected datasets</h2>
{cards}

<h2 style="margin-top:48px;">UI mockup</h2>
<p style="color:#475569;">How the dual score would render on an AQUAVIEW dataset detail page (showing the dataset with the largest FAIR-C ↔ FAIR-H divergence in the sample above):</p>
{mockup}

<footer style="margin-top:64px;padding-top:24px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:12px;">
Generated by <code>fair_benchmark.dual_mvp</code> · AQUAVIEW-DAH/aquaview-fair-benchmark
</footer>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sources", nargs="*", default=SELECTED_SOURCE_KEYS)
    args = ap.parse_args(argv)

    print(f"Loading FAIR-C baseline: {args.report}")
    with open(args.report) as f:
        report = json.load(f)
    baseline_date = report.get("date", "unknown")

    rows: list[tuple[dict, FairHScorecard, dict]] = []
    for src_key in args.sources:
        c_summary = fair_c_summary(report, src_key)
        if not c_summary:
            print(f"  skip {src_key}: not in FAIR-C report")
            continue
        full_coll = fetch_collection(src_key) or {}
        h_card = score_fair_h(full_coll if full_coll else {"id": src_key})
        rows.append((c_summary, h_card, full_coll))
        print(f"  {src_key}: FAIR-C {c_summary['grade']} ({c_summary['score']:.2f}) | FAIR-H {h_card.overall_grade} ({h_card.overall_score:.2f})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_html(rows, baseline_date), encoding="utf-8")
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
