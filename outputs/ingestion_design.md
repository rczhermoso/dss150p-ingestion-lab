# Ingestion Design

Source-to-raw plan for the four ingestible sources. Postgres is
inspection-only in this lab.

| Source | Method | Raw destination | Duplicate key | Incremental state |
|---|---|---|---|---|
| customers.csv | File copy + manifest | `raw/files/customers/` | File SHA-256 | N/A (full snapshot) |
| orders.json | File copy + manifest | `raw/files/orders/` | File SHA-256 | N/A (full snapshot) |
| products.parquet | File copy + manifest | `raw/files/products/` | File SHA-256 | N/A (full snapshot) |
| REST API /api/events | Paginated GET, `updated_after` filter | `raw/api/events.jsonl` | `event_id` | `max(updated_at)` |
| PostgreSQL support_tickets | Inspection only in this lab | N/A | `ticket_id` | Timestamp/CDC strategy — discussed below |

## Notes

### Files (CSV / JSON / Parquet)

- Each run writes a new run-scoped directory under
  `raw/files/<source>/ingest_date=YYYY-MM-DD/run_id=<uuid>/`.
- The file is copied byte-for-byte; no parsing or type conversion occurs
  in the raw layer.
- A manifest records the source path, file size, SHA-256, ingest
  timestamp, and run_id.
- Reruns with unchanged inputs are detected via the SHA-256 manifest
  and skipped — no duplicate raw copies.

### REST API

- Each run appends newline-delimited JSON to `raw/api/events.jsonl`.
- Duplicate prevention: the pipeline records `event_id`s already seen
  and logs how many were re-emitted at a newer `updated_at`.
- Incremental state: a watermark file holds the max `updated_at`
  successfully persisted. On the next run the pipeline requests
  `updated_after=<watermark>`.

### PostgreSQL (design only, not implemented)

- A production-grade strategy would use either:
  - a monotonically increasing **timestamp column** (none present here —
    `opened_at` and `resolved_at` do not capture all updates), or
  - **change data capture (CDC)** via logical replication, which
    captures every row change regardless of timestamp fidelity.
- This lab inspects the source read-only; no ingestion is performed.