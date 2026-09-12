from collections import Counter
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000/api/events"
OUT = Path("outputs/profiling_api.md")
PER_PAGE = 20
TIMEOUT = 10  # seconds per request


def fetch_page(page: int) -> dict:
    """Fetch a single page. Raises on non-2xx or timeout."""
    r = requests.get(
        BASE,
        params={"page": page, "per_page": PER_PAGE},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def walk_all_pages() -> tuple[list[dict], list[int]]:
    """
    Follow pagination until has_more is false.

    Returns (items, pages_visited). Raises if the cursor stalls so a
    misbehaving server cannot hang the script forever.
    """
    items: list[dict] = []
    pages_visited: list[int] = []
    page = 1

    while True:
        payload = fetch_page(page)
        pages_visited.append(payload["page"])
        items.extend(payload["items"])

        if not payload["has_more"]:
            break

        nxt = payload.get("next_page")
        if not nxt or nxt == page:
            raise RuntimeError(f"pagination stalled at page {page}")

        page = nxt

    return items, pages_visited


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # --- First page (shape inspection) ---------------------------------
    first = fetch_page(1)
    sample = first["items"][0]

    # --- Full walk ------------------------------------------------------
    items, pages_visited = walk_all_pages()

    lines: list[str] = []
    lines.append("# Profiling: local REST API\n")
    lines.append(f"- Base URL: `{BASE}`")
    lines.append(f"- per_page: {PER_PAGE}")
    lines.append(f"- Pages visited: {pages_visited}")
    lines.append(f"- Total records fetched: {len(items)}\n")

    # --- Pagination envelope -------------------------------------------
    lines.append("## Pagination envelope (first response)\n")
    lines.append("```")
    for k in ("page", "per_page", "total", "has_more", "next_page"):
        lines.append(f"{k}: {first.get(k)}")
    lines.append(f"len(items): {len(first['items'])}")
    lines.append("```\n")

    # --- Record shape ---------------------------------------------------
    lines.append("## Record shape (first item)\n")
    lines.append("```")
    for k, v in sample.items():
        lines.append(f"{k}: {type(v).__name__}")
    lines.append("```\n")

    lines.append("### Sample record\n")
    lines.append("```")
    for k, v in sample.items():
        lines.append(f"{k}: {v!r}")
    lines.append("```\n")

    # --- Logical roles --------------------------------------------------
    lines.append("## Field roles\n")
    lines.append("| Field | Role | Notes |")
    lines.append("|---|---|---|")
    lines.append("| event_id | identifier | Logical key; duplicates observed |")
    lines.append("| customer_id | identifier | FK to customers.csv |")
    lines.append("| event_type | categorical | Enumerated below |")
    lines.append("| amount | numeric (float) | |")
    lines.append("| updated_at | timestamp | ISO-8601, no timezone; watermark candidate |")
    lines.append("| metadata | nested object | `{channel, campaign}` |")
    lines.append("")

    # --- event_type distribution ---------------------------------------
    lines.append("## `event_type` distribution\n")
    lines.append("```")
    for v, n in Counter(it.get("event_type") for it in items).most_common():
        lines.append(f"{v}: {n}")
    lines.append("```\n")

    # --- Duplicate event_id check --------------------------------------
    ids = [it["event_id"] for it in items]
    counts = Counter(ids)
    dup_ids = {k: v for k, v in counts.items() if v > 1}

    lines.append("## Duplicate `event_id` check\n")
    lines.append(f"Distinct `event_id` values: {len(counts)}")
    lines.append(f"Total records fetched: {len(items)}")
    lines.append(f"Duplicate `event_id`s: {len(dup_ids)}\n")

    if dup_ids:
        lines.append("### Duplicated IDs\n")
        lines.append("| event_id | occurrences | updated_at values |")
        lines.append("|---|---:|---|")
        for eid, n in dup_ids.items():
            stamps = sorted(
                it["updated_at"] for it in items if it["event_id"] == eid
            )
            lines.append(f"| {eid} | {n} | {', '.join(stamps)} |")
        lines.append("")
        lines.append(
            "The source deliberately repeats these IDs with newer "
            "`updated_at` timestamps. Ingestion must treat `event_id` as "
            "the logical key and `updated_at` as the version, applying "
            "last-write-wins semantics. Both raw copies are retained; the "
            "ledger records that the later version supersedes the earlier."
        )
        lines.append("")

    # --- Why page 1 alone is incomplete --------------------------------
    lines.append("## Why processing only page 1 is incomplete\n")
    lines.append(
        f"Page 1 returned {len(first['items'])} of {first['total']} "
        f"records and reported `has_more: {first['has_more']}`. "
        "A pipeline that ingests page 1 only would silently drop the "
        "remainder. Full ingestion must follow `next_page` until "
        "`has_more` is false."
    )
    lines.append("")

    # --- Watermark note -------------------------------------------------
    lines.append("## Watermark candidate\n")
    lines.append(
        "`updated_at` is the natural watermark field: it advances "
        "monotonically for a given `event_id` when a newer version "
        "arrives. The ingestion pipeline reads the last successful "
        "watermark from `state/`, filters the API by `updated_after`, "
        "writes raw output, and only then advances the watermark."
    )

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Fetched {len(items)} records across {len(pages_visited)} pages")


if __name__ == "__main__":
    main()