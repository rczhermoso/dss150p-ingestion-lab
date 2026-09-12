# Profiling: local REST API

- Base URL: `http://127.0.0.1:8000/api/events`
- per_page: 20
- Pages visited: [1, 2, 3, 4, 5, 6, 7]
- Total records fetched: 122

## Pagination envelope (first response)

```
page: 1
per_page: 20
total: 122
has_more: True
next_page: 2
len(items): 20
```

## Record shape (first item)

```
event_id: str
customer_id: str
event_type: str
amount: float
updated_at: str
metadata: dict
```

### Sample record

```
event_id: 'E0001'
customer_id: 'C0024'
event_type: 'page_view'
amount: 4210.54
updated_at: '2026-08-01T11:00:00'
metadata: {'channel': 'partner', 'campaign': 'none'}
```

## Field roles

| Field | Role | Notes |
|---|---|---|
| event_id | identifier | Logical key; duplicates observed |
| customer_id | identifier | FK to customers.csv |
| event_type | categorical | Enumerated below |
| amount | numeric (float) | |
| updated_at | timestamp | ISO-8601, no timezone; watermark candidate |
| metadata | nested object | `{channel, campaign}` |

## `event_type` distribution

```
page_view: 30
add_to_cart: 28
payment: 22
support: 21
checkout: 21
```

## Duplicate `event_id` check

Distinct `event_id` values: 120
Total records fetched: 122
Duplicate `event_id`s: 2

### Duplicated IDs

| event_id | occurrences | updated_at values |
|---|---:|---|
| E0020 | 2 | 2026-08-03T20:00:00, 2026-08-21T09:00:00 |
| E0055 | 2 | 2026-08-08T05:00:00, 2026-08-21T10:00:00 |

The source deliberately repeats these IDs with newer `updated_at` timestamps. Ingestion must treat `event_id` as the logical key and `updated_at` as the version, applying last-write-wins semantics. Both raw copies are retained; the ledger records that the later version supersedes the earlier.

## Why processing only page 1 is incomplete

Page 1 returned 20 of 122 records and reported `has_more: True`. A pipeline that ingests page 1 only would silently drop the remainder. Full ingestion must follow `next_page` until `has_more` is false.

## Watermark candidate

`updated_at` is the natural watermark field: it advances monotonically for a given `event_id` when a newer version arrives. The ingestion pipeline reads the last successful watermark from `state/`, filters the API by `updated_after`, writes raw output, and only then advances the watermark.