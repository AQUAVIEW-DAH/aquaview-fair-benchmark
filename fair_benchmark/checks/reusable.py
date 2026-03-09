"""R -- Reusable checks (R1, R1.1, R1.2, R1.3)."""

from __future__ import annotations

from ..models import CatalogSample, Finding


def check_reusable(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_r1(sample))
    findings.extend(_check_r1_1(sample))
    findings.extend(_check_r1_2(sample))
    findings.extend(_check_r1_3(sample))
    return findings


# ---------------------------------------------------------------------------
# R1: Richly described with accurate and relevant attributes
# ---------------------------------------------------------------------------

# Attributes beyond basic discovery that indicate reusability
REUSE_ATTRIBUTES = {
    "resolution": ["gsd", "resolution", "spatial_resolution", "temporal_resolution",
                    "aquaview:resolution"],
    "quality": ["quality", "uncertainty", "accuracy", "aquaview:quality",
                "processing_level", "aquaview:processing_level"],
    "format": ["media_type", "type", "format"],
    "size": ["file:size", "size", "content-length"],
    "variables": ["variables", "aquaview:variables", "eo:bands"],
}


def _check_r1(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})
        assets = item.get("assets", {})

        categories_found: list[str] = []

        for category, field_names in REUSE_ATTRIBUTES.items():
            # Check properties
            if any(props.get(f) for f in field_names):
                categories_found.append(category)
                continue
            # Check assets
            for asset in assets.values():
                if any(asset.get(f) for f in field_names):
                    categories_found.append(category)
                    break

        # Also check asset media types
        asset_types = [a.get("type", "") for a in assets.values() if a.get("type")]
        if asset_types:
            if "format" not in categories_found:
                categories_found.append("format")

        score = len(categories_found)
        if score >= 4:
            grade = "A"
        elif score >= 3:
            grade = "B"
        elif score >= 2:
            grade = "C"
        elif score >= 1:
            grade = "D"
        else:
            grade = "F"

        missing_cats = [c for c in REUSE_ATTRIBUTES if c not in categories_found]

        findings.append(Finding(
            principle="R1",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=(
                f"reuse_attributes={categories_found}, "
                f"asset_media_types={asset_types[:3]}, "
                f"total_props={len(props)}"
            ),
            gap=f"Missing: {', '.join(missing_cats)}" if missing_cats else "",
            remediation="Add resolution, quality, and size metadata" if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# R1.1: Clear and accessible data usage license
# ---------------------------------------------------------------------------

KNOWN_LICENSES = {
    "cc-by-4.0", "cc-by-sa-4.0", "cc0-1.0", "cc-by-nc-4.0",
    "mit", "apache-2.0", "public-domain", "proprietary",
    "other-open", "other-closed", "various",
}


def _check_r1_1(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})
        links = item.get("links", [])

        license_val = props.get("license") or item.get("license", "")
        has_license = bool(license_val)
        is_known = license_val.lower() in KNOWN_LICENSES if license_val else False

        # Check for license link
        license_links = [l for l in links if l.get("rel") == "license"]
        has_license_link = len(license_links) > 0

        if has_license and is_known and has_license_link:
            grade = "A"
        elif has_license and (is_known or has_license_link):
            grade = "B"
        elif has_license:
            grade = "C"
        else:
            grade = "D"

        gap = ""
        if not has_license:
            gap = "No license field present"
        elif not is_known:
            gap = f"License value '{license_val}' is not a standard SPDX identifier"
        elif not has_license_link:
            gap = "License identified but no license URI/link provided"

        findings.append(Finding(
            principle="R1.1",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=f"license={license_val!r}, known={is_known}, license_link={has_license_link}",
            gap=gap,
            remediation="Add SPDX license identifier and license URI link" if grade != "A" else "",
        ))

    # Collection-level license check
    for coll in sample.collections:
        coll_id = coll.get("id", "unknown")
        license_val = coll.get("license", "")
        has_license = bool(license_val)

        coll_links = coll.get("links", [])
        has_license_link = any(l.get("rel") == "license" for l in coll_links)

        if has_license and has_license_link:
            grade = "A"
        elif has_license:
            grade = "B"
        else:
            grade = "D"

        findings.append(Finding(
            principle="R1.1",
            collection_id=coll_id,
            item_id=None,
            grade=grade,
            evidence=f"collection_license={license_val!r}, license_link={has_license_link}",
            gap="No license on collection" if not has_license else "",
            remediation="Add license to collection metadata" if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# R1.2: Detailed provenance
# ---------------------------------------------------------------------------

PROVENANCE_FIELDS = [
    "created", "updated", "processing:level", "processing:lineage",
    "aquaview:source", "aquaview:source_url", "aquaview:ingested_at",
    "aquaview:processing_level", "providers",
]


def _check_r1_2(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})

        prov_found = [f for f in PROVENANCE_FIELDS if props.get(f)]

        # Check providers array for processing roles
        providers = props.get("providers", [])
        has_processor = any(
            "processor" in (p.get("roles", []) if isinstance(p.get("roles"), list) else [])
            for p in providers
            if isinstance(p, dict)
        )
        has_host = any(
            "host" in (p.get("roles", []) if isinstance(p.get("roles"), list) else [])
            for p in providers
            if isinstance(p, dict)
        )

        # Check for STAC processing extension
        extensions = item.get("stac_extensions", [])
        has_processing_ext = any("processing" in str(e).lower() for e in extensions)

        provenance_signals = len(prov_found) + int(has_processor) + int(has_processing_ext)

        if provenance_signals >= 4:
            grade = "A"
        elif provenance_signals >= 2:
            grade = "B"
        elif provenance_signals >= 1:
            grade = "C"
        elif len(providers) > 0:
            grade = "D"
        else:
            grade = "F"

        gap_parts = []
        if not prov_found:
            gap_parts.append("no provenance fields (created, processing:level, etc.)")
        if not has_processor:
            gap_parts.append("no processor role in providers")
        if not has_processing_ext:
            gap_parts.append("no STAC processing extension")

        findings.append(Finding(
            principle="R1.2",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=(
                f"provenance_fields={prov_found}, providers={len(providers)}, "
                f"processor_role={has_processor}, processing_ext={has_processing_ext}"
            ),
            gap="; ".join(gap_parts) if gap_parts else "",
            remediation="Add processing lineage, ingestion timestamps, and provider roles"
            if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# R1.3: Domain-relevant community standards
# ---------------------------------------------------------------------------

COMMUNITY_STANDARD_INDICATORS = {
    "cf_conventions": ["cf_role", "cf_standard_name", "cf_conventions",
                       "conventions", "Conventions"],
    "acdd": ["naming_authority", "creator_name", "publisher_name",
             "geospatial_lat_min", "geospatial_lon_min",
             "cdm_data_type", "standard_name_vocabulary"],
    "iso_19115": ["iso_19115", "iso19115", "gmd:", "19115"],
    "stac_extensions": [],  # checked separately
}


def _check_r1_3(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})
        extensions = item.get("stac_extensions", [])

        standards_found: list[str] = []

        # Check CF conventions
        all_keys_lower = {k.lower(): k for k in props}
        for indicator in COMMUNITY_STANDARD_INDICATORS["cf_conventions"]:
            if indicator.lower() in all_keys_lower:
                if "CF" not in standards_found:
                    standards_found.append("CF")
                break

        # Check ACDD
        acdd_count = sum(
            1 for indicator in COMMUNITY_STANDARD_INDICATORS["acdd"]
            if indicator.lower() in all_keys_lower
        )
        if acdd_count >= 2:
            standards_found.append("ACDD")

        # Check ISO 19115 references
        all_vals = str(props)
        for indicator in COMMUNITY_STANDARD_INDICATORS["iso_19115"]:
            if indicator.lower() in all_vals.lower():
                if "ISO 19115" not in standards_found:
                    standards_found.append("ISO 19115")
                break

        # STAC extensions count as community standards
        if len(extensions) >= 2:
            standards_found.append(f"STAC-ext({len(extensions)})")
        elif len(extensions) == 1:
            standards_found.append("STAC-ext(1)")

        n = len(standards_found)
        if n >= 3:
            grade = "A"
        elif n >= 2:
            grade = "B"
        elif n >= 1:
            grade = "C"
        else:
            grade = "D"

        gap_parts = []
        if "CF" not in standards_found:
            gap_parts.append("no CF convention attributes")
        if "ACDD" not in standards_found:
            gap_parts.append("no ACDD attributes")
        if not any("STAC-ext" in s for s in standards_found):
            gap_parts.append("no STAC extensions declared")

        findings.append(Finding(
            principle="R1.3",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=f"standards={standards_found}, extensions={extensions}",
            gap="; ".join(gap_parts) if gap_parts else "",
            remediation="Add CF convention attributes and ACDD metadata to items"
            if grade != "A" else "",
        ))

    return findings
