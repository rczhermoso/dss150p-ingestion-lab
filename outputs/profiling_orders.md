# Profiling: orders.json

- File size: 77938 bytes
- Root type: list
- Records: 250

## Top-level keys

```
customer_id
item_count
order_id
order_timestamp
shipping
shipping_fee
status
subtotal
total_amount
```

## Structural consistency

Distinct key-sets: 1
All records share the same top-level key set.

## Null counts per top-level key

```
customer_id: 0
item_count: 0
order_id: 0
order_timestamp: 0
shipping: 0
shipping_fee: 0
status: 0
subtotal: 0
total_amount: 0
```

## Nested `shipping` shape

All 250 records: `['method', 'region']`

## Field roles

| Field | Role | Notes |
|---|---|---|
| order_id | identifier | Candidate primary key |
| customer_id | identifier | FK to customers |
| order_timestamp | timestamp | ISO-8601, no timezone |
| status | categorical | Enumerated below |
| item_count | numeric (integer) | |
| subtotal | numeric (float) | |
| shipping_fee | numeric (float) | |
| total_amount | numeric (float) | |
| shipping | nested object | `{method, region}` |

## `status` distribution

```
Pending: 50
Packed: 44
Shipped: 43
Delivered: 42
Cancelled: 40
Paid: 31
```

## `order_timestamp` parse check

Timestamps failing ISO parse: 0

## Representing `shipping` downstream

Two representations of `shipping` are viable:

**Flattening.** `shipping_region` and `shipping_method` become scalar columns.
- Pros: simple SQL, straightforward Parquet loading, per-column validation.
- Cons: schema couples tightly to the nested shape; any new field inside
  `shipping` requires a schema change; nested arrays would break the model.

**Preservation as a nested struct.** `shipping` stays an object.
- Pros: raw fidelity, tolerant of schema evolution, handles future nesting.
- Cons: requires semi-structured query syntax (`shipping.region` in
  Parquet/DuckDB, `->>` in Postgres).

Because the lab requires the raw area to preserve source values verbatim,
ingestion will use the nested representation. Flattening remains a candidate
for a later analytical layer.


## Candidate validation rules

1. `order_id` — required; must be unique.
2. `customer_id` — required; must be a non-empty string.
3. `order_timestamp` — required; must parse as ISO-8601; must not be in the future.
4. `item_count` — required; integer ≥ 0.
5. `subtotal`, `shipping_fee`, `total_amount` — required; numeric ≥ 0.
6. `status` — required; must be one of the values observed below.
7. `shipping` — required; object with non-null `region` and `method` strings.

## Scope note

No source records were removed or repaired. All findings are documented only, per the lab's engineering constraints.