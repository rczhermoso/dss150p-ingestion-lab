# Profiling: support_tickets (PostgreSQL)

- **Source:** `dss150p` database, `public.support_tickets` table
- **Container:** `dss150p-lab2-postgres`
- **Row count:** 250
- **Primary key:** `support_tickets_pkey` on `ticket_id`
- **Inspection method:** bounded read-only queries (`\d`, `COUNT(*)`,
  `GROUP BY`, `LIMIT 10`). No joins, no full-table scans, no DDL/DML.

---

## Schema

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `ticket_id` | integer | NOT NULL | Primary key |
| `customer_id` | varchar(10) | NOT NULL | References customers.csv IDs (`C####`) |
| `category` | varchar(40) | NOT NULL | 5 distinct values |
| `priority` | varchar(10) | NOT NULL | 3 distinct values |
| `assigned_agent` | varchar(80) | nullable | 4 NULLs |
| `opened_at` | timestamp without time zone | NOT NULL | |
| `resolved_at` | timestamp without time zone | nullable | NULL until resolved |
| `status` | varchar(20) | NOT NULL | 4 distinct values |

Indexes:

- `support_tickets_pkey` PRIMARY KEY, btree (`ticket_id`)

---

## Null counts

- `assigned_agent`: **4 NULL**
- `resolved_at`: NULL for rows whose `status` is `Open` or `In Progress`
  (observed in the 10-row sample, consistent with the status distribution).
- All other columns: 0 NULL.

---

## Categorical values

### status

```
Closed        61
In Progress   69
Open          56
Resolved      64
-----------  ---
total        250
```

### priority

```
High      84
Low       92
Medium    74
--------  ---
total    250
```

### category

```
Account     60
Billing     47
Delivery    49
Product     51
Technical   43
---------  ---
total      250
```

All three columns are NOT NULL and their value counts sum to 250,
confirming no missing values.

---

## Sample observations (10 rows)

```
ticket_id | customer_id | category  | priority | assigned_agent |      opened_at      |     resolved_at     |   status
----------+-------------+-----------+----------+----------------+---------------------+---------------------+-------------
        1 | C0246       | Technical | High     | J. Reyes       | 2026-06-19 04:00:00 | 2026-06-21 13:00:00 | Resolved
        2 | C0130       | Product   | Medium   | J. Reyes       | 2026-05-26 07:00:00 | 2026-05-26 23:00:00 | Closed
        3 | C0094       | Delivery  | Medium   | J. Reyes       | 2026-03-28 09:00:00 | 2026-03-31 17:00:00 | Closed
        4 | C0057       | Technical | High     | L. Tan         | 2026-04-25 19:00:00 |                     | In Progress
        5 | C0120       | Delivery  | High     | R. Cruz        | 2026-01-20 02:00:00 | 2026-01-22 21:00:00 | Resolved
        6 | C0211       | Product   | Medium   | P. Lim         | 2026-02-26 13:00:00 |                     | Open
        7 | C0041       | Delivery  | Low      | P. Lim         | 2026-03-11 23:00:00 |                     | Open
        8 | C0040       | Billing   | Low      | L. Tan         | 2026-02-14 05:00:00 | 2026-02-16 08:00:00 | Resolved
        9 | C0155       | Technical | Low      | R. Cruz        | 2026-02-09 04:00:00 | 2026-02-11 08:00:00 | Resolved
       10 | C0094       | Account   | Low      | J. Reyes       | 2026-04-12 19:00:00 |                     | In Progress
```

- Rows 4, 6, 7, 10 have `status IN ('Open', 'In Progress')` and a NULL
  `resolved_at`. Rows 1, 2, 3, 5, 8, 9 have a populated `resolved_at`
  and a terminal `status` (`Resolved` or `Closed`).
- `customer_id` values use the same `C####` format as customers.csv,
  so cross-source joins are possible in a downstream layer.
- Timestamps are stored as `timestamp without time zone`, matching the
  API's `updated_at` convention.

---

## Field roles

| Field | Role | Notes |
|---|---|---|
| `ticket_id` | identifier | Primary key |
| `customer_id` | identifier | FK to customers dimension |
| `category` | categorical | 5 values |
| `priority` | categorical | 3 values |
| `assigned_agent` | string (nullable) | 4 NULLs |
| `opened_at` | timestamp (no tz) | Required |
| `resolved_at` | timestamp (no tz, nullable) | NULL until resolved |
| `status` | categorical | 4 values |

---

## Candidate validation rules

1. `ticket_id` — required; unique (enforced by primary key).
2. `customer_id` — required; must match the customers dimension format `C####`.
3. `opened_at` — required; must not be in the future.
4. `resolved_at` — if present, must be `>= opened_at`.
5. `resolved_at` — must be NULL when `status IN ('Open', 'In Progress')`.
6. `priority` — must be one of {High, Low, Medium}.
7. `status` — must be one of {Closed, In Progress, Open, Resolved}.
8. `category` — must be one of {Account, Billing, Delivery, Product, Technical}.

---

## Source-system safety notes

- Queries issued during inspection:
  - `\d support_tickets`
  - `SELECT COUNT(*) FROM support_tickets;`
  - `SELECT * FROM support_tickets ORDER BY ticket_id LIMIT 10;`
  - `SELECT COUNT(*) FROM support_tickets WHERE assigned_agent IS NULL;`
  - `SELECT status, COUNT(*) FROM support_tickets GROUP BY status ORDER BY status;`
  - `SELECT priority, COUNT(*) FROM support_tickets GROUP BY priority ORDER BY priority;`
  - `SELECT category, COUNT(*) FROM support_tickets GROUP BY category ORDER BY category;`
- All queries were bounded: no unbounded `SELECT *`, no joins, no
  full-table analytical scans, no DDL or DML.
- The source was inspected read-only.

---

## Scope note

No source records were removed or repaired. Findings are documented only,
per the lab's engineering constraints.