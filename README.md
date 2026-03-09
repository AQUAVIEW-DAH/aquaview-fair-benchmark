# AQUAVIEW FAIR Benchmark

Automated FAIR data principles assessment for the AQUAVIEW oceanographic data platform. Tests all 15 GO-FAIR sub-principles against the live STAC API and produces scored reports at both the **platform level** and **per-source level**.

## Quick Start

```bash
# Install
pip install .

# Run the benchmark
fair-benchmark

# Or run as module
python -m fair_benchmark
```

Reports are saved to `reports/` as both Markdown and JSON.

## What It Measures

The benchmark evaluates the [15 FAIR sub-principles](https://www.go-fair.org/fair-principles/) (Findable, Accessible, Interoperable, Reusable) by querying real data from the AQUAVIEW STAC API:

| Category | Principles | Weight |
|----------|-----------|--------|
| **F**indable | F1 (persistent IDs), F2 (rich metadata), F3 (self-identification), F4 (searchability) | 1.5x |
| **A**ccessible | A1 (retrieval protocol), A1.1 (open protocol), A1.2 (auth support), A2 (metadata persistence) | 1.5x |
| **I**nteroperable | I1 (formal standards), I2 (controlled vocabularies), I3 (qualified references) | 1.0x |
| **R**eusable | R1 (rich attributes), R1.1 (license), R1.2 (provenance), R1.3 (community standards) | 1.0x |

## Output

Each run produces:

1. **Platform scorecard** -- overall FAIR grade across all sources
2. **Per-source leaderboard** -- every data source ranked by FAIR compliance
3. **Per-source detail** -- principle-by-principle breakdown for each source
4. **Gap analysis** -- top issues ranked by how many sources they affect
5. **Remediation roadmap** -- prioritized fix list (quick wins to large efforts)
6. **Delta tracking** -- automatic comparison against the previous run

### Example output

```
Platform FAIR Scorecard: B (2.85/4.00)
┌───────────┬───────┬───────┬────────┬──────────────────────────┐
│ Principle │ Grade │ Score │ Weight │ Gap                      │
├───────────┼───────┼───────┼────────┼──────────────────────────┤
│ F1        │ C     │ 2.10  │ 1.5x   │ No persistent identifier │
│ F2        │ B     │ 3.20  │ 1.5x   │ Missing: keywords        │
│ ...       │       │       │        │                          │
└───────────┴───────┴───────┴────────┴──────────────────────────┘
```

## CLI Options

```
fair-benchmark [OPTIONS]

Options:
  -o, --output-dir DIR   Report output directory (default: ./reports)
  --stac-url URL         Override STAC API URL
  --json-only            Output JSON to stdout (no files saved)
  -v, --verbose          Debug logging
  --version              Show version
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AQUAVIEW_STAC_URL` | Production URL | STAC API base URL |
| `AQUAVIEW_FAIR_TIMEOUT` | `30` | HTTP timeout in seconds |

## CI/CD

A GitHub Actions workflow runs the benchmark weekly and commits results:

- **Schedule:** Every Monday at 8am UTC
- **Manual:** Trigger via `workflow_dispatch` with optional STAC URL override
- **Output:** Results committed to `reports/` with automatic delta tracking

## Project Structure

```
aquaview-fair-benchmark/
├── fair_benchmark/
│   ├── __main__.py         # CLI entry point
│   ├── config.py           # API URL, weights, sample queries
│   ├── sampler.py          # Catalog sampling (search, bbox, get_item, aggregate)
│   ├── scorer.py           # Grade computation and aggregation
│   ├── reporter.py         # Markdown + JSON report generation
│   ├── delta.py            # Run-over-run comparison
│   ├── models.py           # Data models (Finding, Scorecard, etc.)
│   └── checks/
│       ├── findable.py     # F1-F4
│       ├── accessible.py   # A1-A2
│       ├── interoperable.py # I1-I3
│       └── reusable.py     # R1-R1.3
├── reports/                # Generated reports (gittracked)
├── .github/workflows/      # CI automation
└── pyproject.toml
```

## Grading Scale

| Grade | Score | Meaning |
|-------|-------|---------|
| A | 3.5-4.0 | Fully compliant |
| B | 2.5-3.4 | Mostly compliant, minor gaps |
| C | 1.5-2.4 | Partially compliant, significant gaps |
| D | 0.5-1.4 | Minimally compliant |
| F | 0.0-0.4 | Non-compliant |

Grades are computed per-item, aggregated per-source, then rolled up to the platform level. F and A principles are weighted 1.5x because they're the foundation of FAIR.

## Using Results to Improve AQUAVIEW

The per-source breakdown tells you exactly which upstream data sources are dragging down FAIR compliance and what to fix. Common patterns:

- **Low F1 across all sources** -> Add DOI minting to the ingestion pipeline
- **Low I2 on specific sources** -> Map that source's keywords to GCMD vocabulary
- **Low R1.1 everywhere** -> Add license field to collection metadata
- **One source at D while others are B** -> Prioritize enriching that source's metadata
