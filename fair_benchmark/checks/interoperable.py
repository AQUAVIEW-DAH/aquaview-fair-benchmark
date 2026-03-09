"""I -- Interoperable checks (I1, I2, I3)."""

from __future__ import annotations

import re

from ..models import CatalogSample, Finding


def check_interoperable(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_i1(sample))
    findings.extend(_check_i2(sample))
    findings.extend(_check_i3(sample))
    return findings


# ---------------------------------------------------------------------------
# I1: Formal, accessible, shared language for knowledge representation
# ---------------------------------------------------------------------------

ISO_8601_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?"
)


def _check_i1(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})

        # Check STAC type
        is_stac_feature = item.get("type") == "Feature"
        stac_version = item.get("stac_version", "")
        stac_extensions = item.get("stac_extensions", [])

        # Check GeoJSON geometry
        geometry = item.get("geometry")
        has_geojson = (
            geometry is not None
            and isinstance(geometry, dict)
            and geometry.get("type") in (
                "Point", "MultiPoint", "LineString", "MultiLineString",
                "Polygon", "MultiPolygon", "GeometryCollection",
            )
        )

        # Check ISO 8601 datetimes
        dt = props.get("datetime") or props.get("start_datetime") or ""
        has_iso_datetime = bool(ISO_8601_PATTERN.match(str(dt))) if dt else False

        # Check bbox format
        bbox = item.get("bbox")
        has_bbox = isinstance(bbox, list) and len(bbox) in (4, 6)

        standards_met = []
        if is_stac_feature:
            standards_met.append("STAC")
        if has_geojson:
            standards_met.append("GeoJSON")
        if has_iso_datetime:
            standards_met.append("ISO 8601")
        if has_bbox:
            standards_met.append("bbox")
        if stac_extensions:
            standards_met.append(f"extensions({len(stac_extensions)})")

        score = len(standards_met)
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

        gap_parts = []
        if not is_stac_feature:
            gap_parts.append("not a STAC Feature")
        if not has_geojson:
            gap_parts.append("no GeoJSON geometry")
        if not has_iso_datetime:
            gap_parts.append("no ISO 8601 datetime")
        if not stac_extensions:
            gap_parts.append("no STAC extensions declared")

        findings.append(Finding(
            principle="I1",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=(
                f"standards={standards_met}, stac_version={stac_version!r}, "
                f"extensions={stac_extensions}"
            ),
            gap="; ".join(gap_parts) if gap_parts else "",
            remediation="Declare STAC extensions; ensure all items have geometry and datetime"
            if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# I2: Vocabularies that follow FAIR principles
# ---------------------------------------------------------------------------

# Known controlled vocabulary indicators
CONTROLLED_VOCAB_INDICATORS = [
    "gcmd", "cf_standard_name", "cf-standard", "wmo", "ioos",
    "science_keywords", "earth science",
]


def _check_i2(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        props = item.get("properties", {})

        keywords = props.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]

        # Check if keywords appear to use controlled vocabulary
        has_controlled_kw = False
        controlled_indicators: list[str] = []
        for kw in keywords:
            kw_lower = str(kw).lower()
            for indicator in CONTROLLED_VOCAB_INDICATORS:
                if indicator in kw_lower:
                    has_controlled_kw = True
                    controlled_indicators.append(indicator)

        # Check for CF standard name in variable descriptions
        has_cf_names = False
        cf_fields = [k for k in props if "cf_" in k.lower() or "standard_name" in k.lower()]
        if cf_fields:
            has_cf_names = True

        # Check for variable names that look standardized vs informal
        variables = props.get("variables", props.get("aquaview:variables", []))
        has_variables = len(variables) > 0 if isinstance(variables, list) else bool(variables)

        # Check STAC extensions for vocabulary references
        extensions = item.get("stac_extensions", [])
        sci_ext = any("scientific" in str(e).lower() or "sci" in str(e).lower() for e in extensions)

        if has_controlled_kw and has_cf_names:
            grade = "A"
        elif has_controlled_kw or has_cf_names:
            grade = "B"
        elif len(keywords) > 0 or has_variables:
            grade = "C"
            # Keywords exist but aren't from a controlled vocabulary
        elif len(keywords) == 0 and not has_variables:
            grade = "D"
        else:
            grade = "F"

        gap_parts = []
        if not has_controlled_kw:
            gap_parts.append("keywords not from controlled vocabulary (GCMD, CF, etc.)")
        if not has_cf_names:
            gap_parts.append("no CF Standard Names for variables")
        if not has_variables:
            gap_parts.append("no variable metadata")

        findings.append(Finding(
            principle="I2",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=(
                f"keywords={keywords[:3]}, controlled_indicators={controlled_indicators}, "
                f"cf_fields={cf_fields}, has_variables={has_variables}, sci_extension={sci_ext}"
            ),
            gap="; ".join(gap_parts) if gap_parts else "",
            remediation="Map keywords to GCMD Science Keywords; add CF Standard Names to variables"
            if grade != "A" else "",
        ))

    return findings


# ---------------------------------------------------------------------------
# I3: Qualified references to other (meta)data
# ---------------------------------------------------------------------------

BASIC_LINK_RELS = {"self", "parent", "collection", "root", "items", "next", "prev"}


def _check_i3(sample: CatalogSample) -> list[Finding]:
    findings: list[Finding] = []

    for item in sample.all_items:
        coll = item.get("collection", "unknown")
        item_id = item.get("id", "")
        links = item.get("links", [])

        link_rels = {l.get("rel", "") for l in links}
        # Qualified references go beyond basic navigation
        qualified_rels = link_rels - BASIC_LINK_RELS - {""}
        has_qualified = len(qualified_rels) > 0

        # Specific relationship types we'd love to see
        has_derived_from = "derived_from" in link_rels or "derived-from" in link_rels
        has_related = "related" in link_rels
        has_via = "via" in link_rels
        has_alternate = "alternate" in link_rels
        has_cite = "cite-as" in link_rels

        rich_refs = sum([has_derived_from, has_related, has_via, has_cite])

        if rich_refs >= 2:
            grade = "A"
        elif has_qualified:
            grade = "B"
        elif len(links) > 0:
            grade = "C"
            # Has basic STAC links but no qualified references
        else:
            grade = "F"

        gap = ""
        if grade != "A":
            gap = (
                f"Only basic link rels present ({link_rels & BASIC_LINK_RELS}); "
                f"missing qualified references (derived_from, related, cite-as, etc.)"
            )

        findings.append(Finding(
            principle="I3",
            collection_id=coll,
            item_id=item_id,
            grade=grade,
            evidence=(
                f"link_rels={sorted(link_rels)}, "
                f"qualified={sorted(qualified_rels)}, "
                f"derived_from={has_derived_from}, cite_as={has_cite}"
            ),
            gap=gap,
            remediation="Add qualified link relations (derived_from, related, cite-as) to connect datasets"
            if grade != "A" else "",
        ))

    return findings
