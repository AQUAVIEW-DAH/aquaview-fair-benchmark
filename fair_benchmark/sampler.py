"""Catalog sampler: pulls diverse items from the AQUAVIEW STAC API for testing."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import BBOX_QUERIES, HTTP_TIMEOUT, SEARCH_QUERIES, STAC_API_URL

logger = logging.getLogger(__name__)


@dataclass
class CatalogSample:
    """All data collected during the sampling phase."""

    collections: list[dict[str, Any]] = field(default_factory=list)
    search_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    bbox_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    single_item: dict[str, Any] | None = None
    single_item_source: str = ""
    aggregations: dict[str, Any] = field(default_factory=dict)
    total_item_count: int | None = None
    collection_frequency: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def all_items(self) -> list[dict[str, Any]]:
        """Flatten all sampled items into a single list (deduplicated by id)."""
        seen: set[str] = set()
        items: list[dict[str, Any]] = []
        for result in [*self.search_results.values(), *self.bbox_results.values()]:
            for item in result.get("items", []):
                item_id = item.get("id", "")
                if item_id not in seen:
                    seen.add(item_id)
                    items.append(item)
        if self.single_item:
            sid = self.single_item.get("id", "")
            if sid not in seen:
                items.append(self.single_item)
        return items


async def collect_sample(client: httpx.AsyncClient | None = None) -> CatalogSample:
    """Run all sampling queries and return a CatalogSample."""
    sample = CatalogSample()
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(base_url=STAC_API_URL, timeout=HTTP_TIMEOUT)

    try:
        await _list_collections(client, sample)
        await _run_searches(client, sample)
        await _run_bbox_searches(client, sample)
        await _get_single_item(client, sample)
        await _run_aggregations(client, sample)
    finally:
        if own_client:
            await client.aclose()

    return sample


async def _list_collections(client: httpx.AsyncClient, sample: CatalogSample) -> None:
    try:
        resp = await client.get("/collections")
        resp.raise_for_status()
        data = resp.json()
        sample.collections = data.get("collections", [])
        logger.info("list_collections: %d collections", len(sample.collections))
    except Exception as e:
        sample.errors.append(f"list_collections failed: {e}")
        logger.error("list_collections failed: %s", e)


async def _run_searches(client: httpx.AsyncClient, sample: CatalogSample) -> None:
    for query in SEARCH_QUERIES:
        label = query["label"]
        body = {"q": [query["q"]], "limit": 5}
        try:
            resp = await client.post("/search", json=body)
            resp.raise_for_status()
            data = resp.json()
            sample.search_results[label] = {
                "total": data.get("numberMatched", 0),
                "returned": data.get("numberReturned", len(data.get("features", []))),
                "items": data.get("features", []),
            }
            logger.info("%s: %d items", label, sample.search_results[label]["returned"])
        except Exception as e:
            sample.errors.append(f"{label} failed: {e}")
            logger.error("%s failed: %s", label, e)


async def _run_bbox_searches(client: httpx.AsyncClient, sample: CatalogSample) -> None:
    for query in BBOX_QUERIES:
        label = query["label"]
        bbox = [float(x) for x in query["bbox"].split(",")]
        body = {"bbox": bbox, "limit": 5}
        try:
            resp = await client.post("/search", json=body)
            resp.raise_for_status()
            data = resp.json()
            sample.bbox_results[label] = {
                "total": data.get("numberMatched", 0),
                "returned": data.get("numberReturned", len(data.get("features", []))),
                "items": data.get("features", []),
            }
            logger.info("%s: %d items", label, sample.bbox_results[label]["returned"])
        except Exception as e:
            sample.errors.append(f"{label} failed: {e}")
            logger.error("%s failed: %s", label, e)


async def _get_single_item(client: httpx.AsyncClient, sample: CatalogSample) -> None:
    """Pick a collection+item from search results and fetch it directly."""
    # Find a valid item from search results
    for result in sample.search_results.values():
        for item in result.get("items", []):
            collection = item.get("collection")
            item_id = item.get("id")
            if collection and item_id:
                try:
                    resp = await client.get(f"/collections/{collection}/items/{item_id}")
                    resp.raise_for_status()
                    sample.single_item = resp.json()
                    sample.single_item_source = f"{collection}/{item_id}"
                    logger.info("get_item: %s/%s", collection, item_id)
                    return
                except Exception as e:
                    sample.errors.append(f"get_item {collection}/{item_id} failed: {e}")
                    logger.error("get_item failed: %s", e)

    sample.errors.append("get_item: no valid collection/item pair found in search results")


async def _run_aggregations(client: httpx.AsyncClient, sample: CatalogSample) -> None:
    # Total count
    try:
        resp = await client.post("/aggregate", json={"aggregations": ["total_count"]})
        resp.raise_for_status()
        data = resp.json()
        for agg in data.get("aggregations", []):
            if agg.get("name") == "total_count":
                sample.total_item_count = agg.get("value")
        sample.aggregations["total_count"] = data
        logger.info("total_count: %s", sample.total_item_count)
    except Exception as e:
        sample.errors.append(f"aggregate total_count failed: {e}")
        logger.error("aggregate total_count failed: %s", e)

    # Collection frequency
    try:
        resp = await client.post("/aggregate", json={"aggregations": ["collection_frequency"]})
        resp.raise_for_status()
        data = resp.json()
        for agg in data.get("aggregations", []):
            if agg.get("name") == "collection_frequency":
                sample.collection_frequency = agg.get("buckets", [])
        sample.aggregations["collection_frequency"] = data
        logger.info("collection_frequency: %d buckets", len(sample.collection_frequency))
    except Exception as e:
        sample.errors.append(f"aggregate collection_frequency failed: {e}")
        logger.error("aggregate collection_frequency failed: %s", e)
