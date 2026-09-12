# Profiling: customers.csv

- File size: 18183 bytes
- Shape: 250 rows x 7 columns

## dtypes as read by pandas

```
customer_id         str
first_name          str
last_name           str
email               str
city                str
signup_date         str
customer_segment    str
```

## Logical types

| Column | Logical type | Notes |
|---|---|---|
| customer_id | string (identifier) | Opaque ID; not unique in source |
| first_name | string | Free-text |
| last_name | string | Free-text |
| email | string (nullable) | See null counts |
| city | string (nullable) | See null counts |
| signup_date | date | Stored as text in CSV |
| customer_segment | string (categorical) | Enumerated below |

## Nulls per column

```
customer_id         0
first_name          0
last_name           0
email               3
city                2
signup_date         0
customer_segment    0
```

## Exact duplicate rows

Count: 2

## customer_id uniqueness

Duplicate occurrences: 3
Distinct IDs affected: 3

```
customer_id
C0036    2
C0090    2
C0145    2
```

## customer_segment distribution

```
customer_segment
SME             75
Retail          71
Professional    55
Student         49
```

## signup_date parse check

All 250 values parse as dates.
Range: 2025-01-04 to 2026-05-16

## Candidate validation rules

1. `customer_id` — required; must be unique. **Source violates this.**
2. `email` — if present, must match a basic address pattern (`^[^@\s]+@[^@\s]+\.[^@\s]+$`).
3. `signup_date` — required; must parse as ISO date; must not be in the future.
4. `customer_segment` — must be one of the values observed below.
5. `first_name` / `last_name` — required; non-empty strings.

## Scope note

No source records were removed or repaired. All findings are documented only, per the lab's engineering constraints.