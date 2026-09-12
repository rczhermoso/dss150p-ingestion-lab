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

## Watermark semantics

The API watermark is the greatest successfully persisted `updated_at`
value. On the next run, the pipeline requests only records with
`updated_at` strictly greater than the saved watermark. The watermark
is operational state, not source data.

### What could go wrong if the watermark is saved before the raw file is successfully written?

Saving the watermark before the raw write completes means the pipeline
has recorded that it has seen data up to time T, but the raw file does
not actually contain those records. If the process crashes between the
watermark update and the file write, the next run will skip every event
with `updated_at <= T`. Those events are lost forever. The correct
order is: read → write raw → verify raw → *then* advance the watermark.
The watermark is a promise about what is already persisted, so it must
never be advanced ahead of persistence.

### What could go wrong if the source allows multiple records with exactly the same timestamp?

If two or more records share an `updated_at`, a strict `>` filter on the
next run will skip all of them, including any that were not persisted.
The watermark cannot distinguish "the last record at time T" from "some
records at time T are still missing." Depending on the source, this
leads to permanent record loss or duplicate ingestion (if the filter
were `>=`).

### One limitation of this simplified watermark

The simplified watermark cannot represent ties: it is a single scalar
that assumes all records at a given timestamp were persisted together
and none were missed.

### One production-grade mitigation

Use a **composite cursor** — for example `(updated_at, event_id)` — and
advance the watermark to the lexicographically greatest pair that was
successfully persisted. The next run requests records where
`updated_at > cursor.updated_at OR (updated_at = cursor.updated_at AND
event_id > cursor.event_id)`. This handles ties without loss or
duplication.

A complementary mitigation is **idempotent raw writing** with a
deterministic filename (or a primary key on the raw store), so that a
re-read of the same window is harmless.

---