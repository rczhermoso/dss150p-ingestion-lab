"""Paginated API ingestion with dedup and watermark (Tasks 3.2-3.4)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .common import (
    RAW_DIR,
    STATE_DIR,
    atomic_write_bytes,
    atomic_write_json,
    read_json,
    utcnow_iso,
)

API_BASE = "http://127.0.0.1:8000/api/events"
PER_PAGE = 20
TIMEOUT = 10
API_RAW = RAW_DIR / "api" / "events.jsonl"
WATERMARK_PATH = STATE_DIR / "api_watermark.json"


@dataclass
class ApiIngestResult:
    records_read: int = 0
    records_written: int = 0
    duplicates_removed: int = 0
    watermark_before: str | None = None
    watermark_after: str | None = None
    deduped_records: list[dict] = field(default_factory=list)


def _fetch_page(page: int, updated_after: str | None) -> dict:
    params = {"page": page, "per_page": PER_PAGE}
    if updated_after is not None:
        params["updated_after"] = updated_after
    try:
        r = requests.get(API_BASE, params=params, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.HTTPError as e:
        raise RuntimeError(f"HTTP error on page {page}: {e}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Request failed on page {page}: {e}") from e
    return r.json()


def _walk_all_pages(updated_after: str | None) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        payload = _fetch_page(page, updated_after)
        items.extend(payload["items"])
        if not payload["has_more"]:
            break
        nxt = payload.get("next_page")
        if not nxt or nxt == page:
            raise RuntimeError(f"pagination stalled at page {page}")
        page = nxt
    return items


def _dedupe_by_event_id(items: list[dict]) -> tuple[list[dict], int]:
    """Keep one record per event_id: the one with the greatest updated_at."""
    best: dict[str, dict] = {}
    for item in items:
        eid = item.get("event_id")
        if eid is None:
            continue
        cur = best.get(eid)
        if cur is None or item["updated_at"] > cur["updated_at"]:
            best[eid] = item
    removed = len(items) - len(best)
    return list(best.values()), removed


def ingest_api(run_id: str) -> ApiIngestResult:
    state = read_json(WATERMARK_PATH, default=None)
    watermark_before = state.get("watermark") if state else None

    raw_items = _walk_all_pages(watermark_before)
    deduped, removed = _dedupe_by_event_id(raw_items)

    # Attach ingestion metadata.
    ingested_at = utcnow_iso()
    for rec in deduped:
        rec["_ingested_at"] = ingested_at
        rec["_source"] = "api/events"

    # Append-only write to raw/api/events.jsonl.
    API_RAW.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, sort_keys=True) + "\n" for r in deduped)
    existing = API_RAW.read_bytes() if API_RAW.exists() else b""
    atomic_write_bytes(API_RAW, existing + payload.encode("utf-8"))

    # Compute new watermark ONLY after raw write succeeded.
    new_watermark = max((r["updated_at"] for r in deduped), default=watermark_before)
    atomic_write_json(
        WATERMARK_PATH,
        {"watermark": new_watermark, "updated_at": ingested_at, "run_id": run_id},
    )

    return ApiIngestResult(
        records_read=len(raw_items),
        records_written=len(deduped),
        duplicates_removed=removed,
        watermark_before=watermark_before,
        watermark_after=new_watermark,
        deduped_records=deduped,
    )