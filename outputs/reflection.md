# Engineering Reflection

## 1. Why should source profiling occur before implementation of ingestion?

Profiling establishes ground truth about a source's shape, quality, and
quirks before any pipeline is written. Without it, ingestion code is
written against assumptions. In this lab, the profiling phase revealed
that `customers.csv` has duplicate `customer_id` values, that
`orders.json` nests `shipping`, and that the API deliberately repeats
`event_id`s with newer `updated_at` values. Each of those findings
directly shaped a pipeline decision: the CSV candidate key cannot be
treated as unique, nested objects must be preserved in the raw layer,
and the API requires last-write-wins plus a watermark. Writing the
pipeline first would have hidden these issues until failures appeared
at runtime.

## 2. What is the difference between source event time/updated_at and ingestion time?

Source event time (or `updated_at`) is when the event occurred or was
last modified in the source system. It is a property of the data, it
travels with each record, and it does not change after the fact.
Ingestion time is when the pipeline read and persisted the record. It
is a property of the pipeline run, not the source. In this lab, each
API record carries `_ingested_at` alongside the source's `updated_at`.
They serve different purposes: `updated_at` drives the watermark and
deduplication; `_ingested_at` provides operational traceability for
auditing and debugging. Conflating the two makes the watermark
unreliable.

## 3. Why is event_id alone insufficient to decide which duplicate API record to keep in this exercise?

Because the source deliberately emits the same `event_id` more than
once with different `updated_at` values. Two records can share an
`event_id` and still represent different versions of the same logical
event. If the pipeline kept the first-seen record or the last-arriving
record, it would keep whichever version happened to arrive in a
particular order, which is not a reliable rule. The correct rule is to
keep the record with the greatest `updated_at` per `event_id`. That is
a deterministic, order-independent choice.

## 4. Why must watermark state advance only after successful persistence?

The watermark is a promise about what is already stored. If it advances
before the raw file is written and the process crashes, the next run
will skip everything at or before the new watermark — including records
that were never actually persisted. Those records are then lost
forever. In this lab, ingestion order is: fetch, deduplicate, write
raw, verify raw, then advance the watermark. The failed run documented
in `outputs/evidence/failure_recovery.txt` shows exactly why this
matters: the pipeline errored, the raw file was untouched, and
`api_watermark.json` retained its prior value, so no data was skipped
silently.

## 5. What limitation does `updated_after > watermark` have when multiple source records can share exactly the same timestamp?

If several records share an `updated_at`, a strict greater-than filter
on the next run skips all of them. The watermark cannot distinguish
"all records at time T are persisted" from "some records at time T are
still missing." The result is silent data loss. This is a genuine
limitation of the simplified scalar watermark.

A production-grade mitigation is a composite cursor:
`(updated_at, event_id)`. The watermark stores the greatest pair that
was successfully persisted, and the next run fetches records where
`updated_at > cursor.updated_at OR (updated_at = cursor.updated_at AND
event_id > cursor.event_id)`. This handles ties without loss or
duplication.

## 6. How is duplicate prevention related to idempotency?

Duplicate prevention keeps one logical record per key within a single
run. Idempotency guarantees that rerunning the pipeline with unchanged
inputs produces the same logical result. They are closely related:
idempotency in this lab is enforced through two mechanisms —
deterministic dedup on `event_id` for the API, and content-hash
skipping for files. A rerun over unchanged sources produces zero new
logical records, because the same dedup and skip logic applies. Without
duplicate prevention, reruns would accumulate duplicates and the
pipeline would not be idempotent.

## 7. Why should the raw area preserve source values instead of applying business transformations?

The raw area is the system of record for what the source actually sent.
Any transformation applied there is irreversible and destroys
information needed for auditing, debugging, and re-processing. Business
logic (type coercion, normalization, deduplication for analytical use)
also tends to change over time, whereas source values do not. Preserving
them exactly means a downstream layer can reprocess history with new
rules whenever required. In this lab, nested `shipping` objects and
JSON-typed numbers are kept verbatim in `raw/`; flattening or typing
belongs to a later lifecycle stage.

## 8. How could querying a production OLTP source for profiling or extraction degrade the application?

An OLTP database is tuned for many small, indexed reads and writes. A
profiling scan (`SELECT *` without a limit, an unindexed aggregate, a
large cross join) consumes CPU, I/O, and buffer-pool memory that the
application needs for live traffic. Long-running queries can hold
snapshots open, delay vacuum, and cause lock contention. In this lab,
all Postgres inspection was bounded: schema inspection, `COUNT(*)`,
`GROUP BY` over 250 rows, and `LIMIT 10`. No joins, no full-table
analytical scans, no destructive statements.

## 9. What would you change if the API had a rate limit of 60 requests per minute?

The pipeline would need to pace its calls and handle 429 responses
gracefully. Concretely: add a small delay between page requests to stay
under the limit (for example, one request per second gives 60 per
minute with headroom), honor `Retry-After` headers when a 429 is
returned, and make the pagination loop idempotent so a mid-run abort
can resume without double-fetching. For high-volume sources, increasing
`per_page` reduces the number of requests per run and is usually the
first optimization. A persistent cursor (`updated_after`) also helps,
since each run fetches only new data rather than re-reading history.

## 10. How would you extend this pipeline from a local raw area to PostgreSQL while preserving rerun safety?

The local pattern is: deduplicated records are appended to
`raw/api/events.jsonl`; state lives in `state/api_watermark.json`. To
extend it to Postgres, keep the same separation of concerns but replace
the raw file with a table. Each row would carry the source fields plus
`_ingested_at`, `_source`, and `_run_id`. Rerun safety comes from a
primary key on `(event_id, updated_at)` (or an upsert that keeps the
row with the greatest `updated_at` per `event_id`). The watermark stays
in a small state table — one row per source — and is updated in the
same transaction that writes the batch. If the transaction commits, the
watermark advances; if it rolls back, the watermark does not. That
preserves the ordering constraint from Task 3.4 (persist first, then
advance state) in a database-native way.