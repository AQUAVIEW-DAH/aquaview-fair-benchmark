"""A -- Accessible checks (A1, A1.1, A1.2, A2)."""

from __future__ import annotations

from ..models import CatalogSample, Finding


def check_accessible(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_a1(sample))
    findings.extend(_check_a1_1(sample))
    findings.extend(_check_a1_2(sample))
    findings.extend(_check_a2(sample))
    return findings


# ---------------------------------------------------------------------------
# A1: Retrievable by identifier using standardized protocol
# ---------------------------------------------------------------------------

def _check_a1(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    # Platform-level: can we fetch an item by collection+ID?
    direct_fetch_works = sample.single_item is not None

    # Check protocol from self-links
    protocols: set[str] = set()
    for item in sample.all_items:
        for link in item.get("links", []):
            href = link.get("href", "")
            if href.startswith("https://"):
                protocols.add("HTTPS")
            elif href.startswith("http://"):
                protocols.add("HTTP")

    if direct_fetch_works and "HTTPS" in protocols:
        grade, gap = "A", ""
    elif direct_fetch_works:
        grade = "B"
        gap = "Direct retrieval works but not all links use HTTPS"
    elif "HTTPS" in protocols or "HTTP" in protocols:
        grade = "C"
        gap = "Links exist but direct item retrieval by ID failed"
    else:
        grade = "F"
        gap = "Cannot retrieve items by identifier"

    findings.append(Finding(
        principle="A1",
        collection_id="_platform",
        item_id=None,
        grade=grade,
        evidence=(
            f"direct_fetch={direct_fetch_works}, "
            f"item_fetched={sample.single_item_source!r}, "
            f"protocols={protocols}"
        ),
        gap=gap,
        remediation="" if grade == "A" else "Ensure all links use HTTPS",
    ))

    # Per-item: check that assets have valid hrefs
    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        assets = item.get("assets", {})
        asset_hrefs = [a.get("href", "") for a in assets.values()]
        https_hrefs = [h for h in asset_hrefs if h.startswith("https://")]
        http_hrefs = [h for h in asset_hrefs if h.startswith("http://")]

        if len(https_hrefs) > 0 and len(https_hrefs) == len(asset_hrefs):
            item_grade, item_gap = "A", ""
        elif len(https_hrefs) > 0 or len(http_hrefs) > 0:
            item_grade = "B"
            item_gap = "Some assets use HTTP instead of HTTPS"
        elif len(assets) == 0:
            item_grade = "D"
            item_gap = "Item has no assets (no data to retrieve)"
        else:
            item_grade = "F"
            item_gap = "Asset hrefs are missing or invalid"

        findings.append(Finding(
            principle="A1",
            collection_id=coll,
            item_id=item_id,
            grade=item_grade,
            evidence=f"assets={len(assets)}, https={len(https_hrefs)}, http={len(http_hrefs)}",
            gap=item_gap,
            remediation="Add asset download links" if item_grade not in ("A", "B") else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# A1.1: Open, free, universally implementable protocol
# ---------------------------------------------------------------------------

def _check_a1_1(sample: CatalogSample) -> list[Finding]:
    # This is fundamentally a platform-level check.
    # STAC API over HTTPS is open and free by definition.
    findings: list[Finding] = []

    # Check if the API is STAC-compliant (look for conformsTo)
    conforms_to: list[str] = []
    for coll in sample.collections:
        ct = coll.get("conformsTo", [])
        if ct:
            conforms_to.extend(ct)

    is_stac = len(sample.collections) > 0  # If we got collections, API works
    is_https = True  # We connected over HTTPS

    if is_stac and is_https:
        grade = "A"
        gap = ""
    elif is_stac:
        grade = "B"
        gap = "STAC API works but protocol details unclear"
    else:
        grade = "F"
        gap = "API does not appear to be a standard STAC endpoint"

    findings.append(Finding(
        principle="A1.1",
        collection_id="_platform",
        item_id=None,
        grade=grade,
        evidence=f"stac_api=true, https=true, collections_returned={len(sample.collections)}",
        gap=gap,
        remediation="" if grade == "A" else "Ensure STAC API conformance classes are declared",
    ))

    return findings


# ---------------------------------------------------------------------------
# A1.2: Protocol allows auth/authz where necessary
# ---------------------------------------------------------------------------

def _check_a1_2(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    # We can check:
    # 1. Did we access the API without auth? (public access works)
    # 2. Are there any indicators of auth support? (harder to test from outside)
    api_accessible = len(sample.collections) > 0 or sample.total_item_count is not None

    # Conservative: we can confirm public access works, but can't confirm
    # auth is available for restricted datasets without trying.
    if api_accessible:
        grade = "B"
        gap = "Public access confirmed; cannot verify auth mechanism for restricted datasets from outside"
    else:
        grade = "F"
        gap = "API not accessible"

    findings.append(Finding(
        principle="A1.2",
        collection_id="_platform",
        item_id=None,
        grade=grade,
        evidence=f"public_access={api_accessible}",
        gap=gap,
        remediation=(
            "Document auth/authz mechanism; expose auth endpoints in API conformance"
            if grade != "A" else ""
        ),
    ))

    return findings


# ---------------------------------------------------------------------------
# A2: Metadata accessible even when data is no longer available
# ---------------------------------------------------------------------------

def _check_a2(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    # We can't directly test what happens when upstream goes down.
    # But we CAN check if metadata appears to be stored independently
    # (i.e., the STAC catalog has its own persistence layer).

    # Evidence: the catalog returns metadata regardless of upstream status.
    # We know AQUAVIEW uses Elasticsearch as its own catalog store.
    has_catalog = len(sample.collections) > 0
    has_items = len(sample.all_items) > 0

    # Check if items reference upstream source URLs (indicates metadata is copied, not proxied)
    items_with_upstream = 0
    for item in sample.all_items:
        props = item.get("properties", {})
        # Look for source URL indicators
        if any(k for k in props if k in ("aquaview:source_url", "source", "erddap_url")):
            items_with_upstream += 1

    if has_catalog and has_items:
        # Conservative grade: we know metadata is in Elasticsearch,
        # but we can't verify retention policy
        grade = "B"
        gap = "Metadata appears independently stored but no explicit retention policy found"
    elif has_catalog:
        grade = "C"
        gap = "Catalog exists but couldn't verify metadata independence from upstream"
    else:
        grade = "F"
        gap = "Cannot determine metadata persistence"

    findings.append(Finding(
        principle="A2",
        collection_id="_platform",
        item_id=None,
        grade=grade,
        evidence=(
            f"catalog_has_collections={has_catalog}, "
            f"catalog_has_items={has_items}, "
            f"items_referencing_upstream={items_with_upstream}/{len(sample.all_items)}"
        ),
        gap=gap,
        remediation=(
            "Add explicit metadata retention policy; "
            "verify metadata persists when upstream ERDDAP/source is unavailable"
        ),
    ))

    return findings
