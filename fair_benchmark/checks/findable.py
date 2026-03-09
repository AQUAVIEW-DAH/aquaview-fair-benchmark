"""F — Findable checks (F1-F4).

All check functions receive a list of items and return a list of Finding objects.
Each Finding is scoped to a collection_id so results can be aggregated per source.
"""

from __future__ import annotations

from ..models import CatalogSample, Finding


def check_findable(sample: CatalogSample) -> list[Finding]:
    """Run all Findable checks against the sample."""
    findings: list[Finding] = []
    findings.extend(_check_f1(sample))
    findings.extend(_check_f2(sample))
    findings.extend(_check_f3(sample))
    findings.extend(_check_f4(sample))
    return findings


# ---------------------------------------------------------------------------
# F1: Globally unique and persistent identifiers
# ---------------------------------------------------------------------------

PERSISTENT_ID_PREFIXES = ("doi:", "https://doi.org/", "ark:", "hdl:", "urn:")


def _check_f1(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})

        has_id = bool(item_id)
        # Check for persistent identifiers (DOI, ARK, handle, etc.)
        has_persistent = False
        persistent_ids: list[str] = []

        # Check common fields for DOIs/persistent IDs
        for field_name in ("doi", "sci:doi", "properties.doi"):
            val = props.get(field_name.replace("properties.", ""), "")
            if val and any(val.lower().startswith(p) for p in PERSISTENT_ID_PREFIXES):
                has_persistent = True
                persistent_ids.append(val)

        # Check links for DOI references
        for link in item.get("links", []):
            href = link.get("href", "")
            if "doi.org" in href:
                has_persistent = True
                persistent_ids.append(href)

        # Check self link stability
        self_links = [l for l in item.get("links", []) if l.get("rel") == "self"]
        has_self_link = len(self_links) > 0

        if has_persistent:
            grade, gap = "A", ""
        elif has_id and has_self_link:
            grade = "C"
            gap = "Platform-internal ID only — no persistent identifier (DOI, ARK, etc.)"
        elif has_id:
            grade = "D"
            gap = "Has internal ID but no self-link and no persistent identifier"
        else:
            grade = "F"
            gap = "No identifier found"

        findings.append(Finding(
            principle="F1",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=f"id={item_id!r}, persistent_ids={persistent_ids}, self_link={has_self_link}",
            gap=gap,
            remediation="Add DOI or persistent identifier field to item metadata" if grade != "A" else "",
        ))

    # Collection-level check
    for coll in sample.collections:
        coll_id = coll.get("id", "unknown")
        coll_links = coll.get("links", [])
        has_doi = any("doi.org" in l.get("href", "") for l in coll_links)
        has_self = any(l.get("rel") == "self" for l in coll_links)

        if has_doi:
            grade, gap = "A", ""
        elif has_self:
            grade = "C"
            gap = "Collection has self-link but no DOI or persistent ID"
        else:
            grade = "D"
            gap = "Collection lacks both persistent ID and self-link"

        findings.append(Finding(
            principle="F1",
            collection_id=coll_id,
            item_id=None,
            grade=grade,
            evidence=f"collection={coll_id}, has_doi={has_doi}, has_self={has_self}",
            gap=gap,
            remediation="Assign DOI to collection" if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# F2: Rich metadata
# ---------------------------------------------------------------------------

# Fields we expect for "rich" metadata
RICH_METADATA_FIELDS = [
    "title", "description", "datetime", "start_datetime", "end_datetime",
    "keywords", "license", "providers", "instruments", "platform",
    "constellation", "gsd", "eo:bands", "sci:citation",
]

# Minimum fields for basic metadata
BASIC_FIELDS = ["title", "datetime"]

# Fields we consider "rich" beyond basic
ENRICHMENT_FIELDS = [
    "description", "keywords", "providers", "instruments", "platform",
    "sci:citation", "sci:doi",
]


def _check_f2(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})

        present = [f for f in RICH_METADATA_FIELDS if props.get(f)]
        basic_present = [f for f in BASIC_FIELDS if props.get(f)]
        enrichment_present = [f for f in ENRICHMENT_FIELDS if props.get(f)]

        total_possible = len(RICH_METADATA_FIELDS)
        pct = len(present) / total_possible if total_possible else 0

        # Also check for AQUAVIEW-specific enrichment fields
        aq_fields = [k for k in props if k.startswith("aquaview:")]
        has_description = bool(props.get("description") or props.get("title"))

        if pct >= 0.6 and len(enrichment_present) >= 3:
            grade = "A"
        elif pct >= 0.4 and has_description:
            grade = "B"
        elif len(basic_present) == len(BASIC_FIELDS) and has_description:
            grade = "C"
        elif len(basic_present) > 0:
            grade = "D"
        else:
            grade = "F"

        missing = [f for f in RICH_METADATA_FIELDS if not props.get(f)]

        findings.append(Finding(
            principle="F2",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=(
                f"present={present}, aquaview_fields={aq_fields}, "
                f"completeness={pct:.0%} ({len(present)}/{total_possible})"
            ),
            gap=f"Missing: {', '.join(missing[:5])}" if missing else "",
            remediation="Populate missing metadata fields from upstream source" if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# F3: Metadata includes identifier of data it describes
# ---------------------------------------------------------------------------

def _check_f3(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        links = item.get("links", [])

        has_self = any(l.get("rel") == "self" for l in links)
        has_id_in_props = bool(item.get("id"))
        has_assets = len(item.get("assets", {})) > 0
        # Can you navigate from metadata to data?
        asset_hrefs = [a.get("href") for a in item.get("assets", {}).values() if a.get("href")]

        if has_id_in_props and has_self and has_assets:
            grade, gap = "A", ""
        elif has_id_in_props and has_assets:
            grade = "B"
            gap = "Has ID and data links but no self-link"
        elif has_id_in_props:
            grade = "C"
            gap = "Has ID but no asset links to navigate to actual data"
        else:
            grade = "F"
            gap = "Metadata does not contain its own identifier"

        findings.append(Finding(
            principle="F3",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=f"has_id={has_id_in_props}, self_link={has_self}, assets={len(asset_hrefs)}",
            gap=gap,
            remediation="Add self-link and ensure asset hrefs are populated" if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# F4: Registered/indexed in a searchable resource
# ---------------------------------------------------------------------------

def _check_f4(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    # This is a platform-level check, not per-item.
    # We grade based on what search capabilities work.
    freetext_works = any(
        r.get("returned", 0) > 0 for r in sample.search_results.values()
    )
    bbox_works = any(
        r.get("returned", 0) > 0 for r in sample.bbox_results.values()
    )
    total_indexed = sample.total_item_count or 0

    if freetext_works and bbox_works and total_indexed > 1000:
        grade = "A"
        gap = ""
    elif freetext_works and bbox_works:
        grade = "B"
        gap = f"Search works but catalog is small ({total_indexed} items)"
    elif freetext_works or bbox_works:
        grade = "C"
        gap = "Only one search modality works"
    else:
        grade = "F"
        gap = "Search is non-functional"

    # Per-collection: check if each collection has indexed items
    for coll_bucket in sample.collection_frequency:
        coll_id = coll_bucket.get("key", "unknown")
        count = coll_bucket.get("frequency", 0)

        if count > 100:
            coll_grade = "A"
            coll_gap = ""
        elif count > 0:
            coll_grade = "B"
            coll_gap = f"Only {count} items indexed"
        else:
            coll_grade = "D"
            coll_gap = "Collection exists but has 0 indexed items"

        findings.append(Finding(
            principle="F4",
            collection_id=coll_id,
            item_id=None,
            grade=coll_grade,
            evidence=f"indexed_items={count}, freetext={freetext_works}, bbox={bbox_works}",
            gap=coll_gap,
            remediation="Ensure items are being indexed from this source" if coll_grade != "A" else "",
        ))

    # Platform-level finding
    findings.append(Finding(
        principle="F4",
        collection_id="_platform",
        item_id=None,
        grade=grade,
        evidence=(
            f"total_indexed={total_indexed}, freetext={freetext_works}, "
            f"bbox={bbox_works}, collections={len(sample.collections)}"
        ),
        gap=gap,
        remediation="Add temporal search support" if grade != "A" else "",
    ))

    return findings
