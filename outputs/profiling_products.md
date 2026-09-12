# Profiling: products.parquet

- File size: 14652 bytes
- Rows: 200
- Columns: 7
- Row groups: 1

## Arrow schema

```
product_id: string not null
product_name: string not null
category: string not null
brand: string not null
unit_price: double not null
stock_quantity: int32 not null
weight_kg: double not null
```

## Logical roles

| Column | Arrow type | Logical type | Notes |
|---|---|---|---|
| product_id | string | identifier | Candidate primary key |
| product_name | string | text |  |
| category | string | categorical | Dictionary-encoded |
| brand | string | categorical | Dictionary-encoded |
| unit_price | double | numeric (float) |  |
| stock_quantity | int32 | numeric (integer) |  |
| weight_kg | double | numeric (float) |  |

## Type preservation

Unlike CSV (all text) and JSON (no schema), Parquet preserves column types and nullability in the file footer. `stock_quantity` is `int32`, not a string or a float. Every column is declared `NOT NULL` at the file level, so nullability need not be inferred from a full scan.

## Format comparison

Generated equivalent CSV and JSON siblings from the Parquet source for a controlled comparison (the optional same-data siblings were not supplied with the lab package).

| Format | Size (bytes) | Ratio vs Parquet | `stock_quantity` type |
|---|---:|---:|---|
| Parquet | 14,652 | 1.00× | int32 |
| CSV | 11,560 | 0.79× | int64 (widened) |
| JSON | 39,286 | 2.68× | int64 (widened) |

CSV is smaller than Parquet at this scale because Parquet's footer (schema, column statistics, row-group metadata) is amortized over only 200 rows. Parquet's compression advantage emerges at larger volumes. JSON is the largest format because every key is repeated on every record.

CSV cannot express column type at all; re-reading widens int32 to int64 and infers nullability from emptiness. JSON preserves numeric-vs-string at the value level but not the declared column type or nullability. Parquet is the only format that preserves (a) integer width, (b) the NOT NULL declaration, and (c) column statistics usable for predicate pushdown — all without reading a single row.

## Why an analytics format is not a common operational source

Parquet is a columnar, compressed, batch-oriented format optimized for
storage and analytical scans. It is not a common operational source because:

1. Live systems emit row-at-a-time JSON or OLTP rows, not columnar files.
2. Appending to Parquet rewrites row groups, which does not match live
   write patterns.
3. Parquet encodes a fixed schema at write time, while operational sources
   often evolve fields without coordination.

Ingestion therefore receives JSON or row-based data and converts to Parquet
in the raw or curated layer, rather than expecting Parquet as a source.
