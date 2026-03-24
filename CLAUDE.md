# AQUAVIEW FAIR Benchmark

Automated FAIR data assessment for the AQUAVIEW platform.

## Run
```bash
.venv/bin/python -m fair_benchmark
```
Or use the `/fair-assessment` slash command.

## Architecture
- Hits live STAC API (`aquaview-sfeos-*.run.app`) directly — no MCP needed
- 15 GO-FAIR sub-principles, F+A weighted 1.5x
- Both levels: platform-wide scorecard + per-source (collection) leaderboard
- Reports: `reports/AQUAVIEW_FAIR_Assessment_YYYY-MM-DD.{md,json}`
- Auto delta tracking between runs

## CI
GitHub Actions weekly run (Monday 8am UTC), commits results to repo.

## Baseline (2026-03-09)
38 collections, 346K items, overall B (2.87/4.00)

## Top Gaps
- F1: no DOIs
- F2: sparse metadata
- I2: no controlled vocabularies

## FAIR-C / FAIR-H Dual Framework
Evolving toward a dual-scoring model:
- **FAIR-C (Computational):** Current benchmark — machine-actionable assessment via 15 GO-FAIR sub-principles
- **FAIR-H (Human):** Experiential assessment — search discoverability, click friction, credential barriers, format accessibility (based on Warren Wood/NRL framework)
- Literature review: `references/FAIR_dual_framework_literature.md`
- Notion spec updated with dual-framework section: https://www.notion.so/31efafad6dcd819d944cc6013bcee268
- Potential *Scientific Data* paper — waiting on Henry's review of email draft to Warren Wood

## Current Status
- **Working on**: FAIR-C/FAIR-H dual framework formalization
- **Done this session**:
  - Added `references/FAIR_dual_framework_literature.md` with 15+ key citations
  - Updated Notion product spec with dual-framework section, prior work, and gap statement
  - Generated PDF spec for email attachment (`~/Downloads/FAIR_Data_Benchmark_Spec.pdf`)
  - Drafted email to Warren Wood (NRL) proposing collaboration — sent to Henry for review
- **Decisions**:
  - FAIR-C/FAIR-H split is the framing (not entirely novel insight, but operationalization is the gap)
  - Lead with FAIR-H externally (less threatening to data providers), FAIR-C internally
  - Cite Vogt (FAIREr/CLEAR), Kenney & Read (usability gap), Benis et al. prominently
- **Next steps**:
  - Get Henry's feedback on email draft, then send to Warren
  - If Warren is interested, outline the paper structure
  - Build FAIR-H scoring prototype (operationalize Warren's metrics)
- **Blocked on**: Henry reviewing email draft (2026-03-24)
- **Session date**: 2026-03-24

## Repo
`AQUAVIEW-DAH/aquaview-fair-benchmark` (public)
