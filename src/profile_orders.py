"""
Profile data/orders.json and write a reproducible evidence report.

Outputs:
    outputs/profiling_orders.md

Design notes:
- Reads the source as-is. Never mutates or repairs records.
- All numeric findings are regenerated on each run.
"""

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

SRC = Path("data/orders.json")
OUT = Path("outputs/profiling_orders.md")

NUMERIC_FIELDS = ["item_count", "subtotal", "shipping_fee", "total_amount"]

VALIDATION_RULES = [
    "`order_id` — required; must be unique.",
    "`customer_id` — required; must be a non-empty string.",
    "`order_timestamp` — required; must parse as ISO-8601; must not be in the future.",
    "`item_count` — required; integer ≥ 0.",
    "`subtotal`, `shipping_fee`, `total_amount` — required; numeric ≥ 0.",
    "`status` — required; must be one of the values observed below.",
    "`shipping` — required; object with non-null `region` and `method` strings.",
]

DOWNSTREAM_REPRESENTATION = """\
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
"""

SCOPE_NOTE = (
    "No source records were removed or repaired. "
    "All findings are documented only, per the lab's engineering constraints."
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC.read_text(encoding="utf-8"))

    lines: list[str] = []

    # --- Header ---------------------------------------------------------
    lines.append("# Profiling: orders.json\n")
    lines.append(f"- File size: {os.path.getsize(SRC)} bytes")
    lines.append(f"- Root type: {type(data).__name__}")
    lines.append(f"- Records: {len(data)}\n")

    # --- Top-level keys -------------------------------------------------
    keys = sorted(data[0].keys())
    lines.append("## Top-level keys\n")
    lines.append("```")
    for k in keys:
        lines.append(k)
    lines.append("```\n")

    # --- Key-set consistency -------------------------------------------
    keysets = Counter(tuple(sorted(r.keys())) for r in data)
    lines.append("## Structural consistency\n")
    lines.append(f"Distinct key-sets: {len(keysets)}")
    if len(keysets) == 1:
        lines.append("All records share the same top-level key set.\n")
    else:
        for ks, n in keysets.items():
            lines.append(f"- {n} records with keys: {ks}")
        lines.append("")

    # --- Nulls per key --------------------------------------------------
    lines.append("## Null counts per top-level key\n")
    lines.append("```")
    for k in keys:
        n = sum(1 for r in data if r.get(k) is None)
        lines.append(f"{k}: {n}")
    lines.append("```\n")

    # --- Nested shipping shape -----------------------------------------
    shipping_keysets = Counter(
        tuple(sorted((r.get("shipping") or {}).keys())) for r in data
    )
    lines.append("## Nested `shipping` shape\n")
    if len(shipping_keysets) == 1:
        shape = next(iter(shipping_keysets))
        lines.append(f"All {len(data)} records: `{list(shape)}`\n")
    else:
        for ks, n in shipping_keysets.items():
            lines.append(f"- {n} records with shipping keys: {ks}")
        lines.append("")

    # --- Field roles ----------------------------------------------------
    lines.append("## Field roles\n")
    lines.append("| Field | Role | Notes |")
    lines.append("|---|---|---|")
    lines.append("| order_id | identifier | Candidate primary key |")
    lines.append("| customer_id | identifier | FK to customers |")
    lines.append("| order_timestamp | timestamp | ISO-8601, no timezone |")
    lines.append("| status | categorical | Enumerated below |")
    lines.append("| item_count | numeric (integer) | |")
    lines.append("| subtotal | numeric (float) | |")
    lines.append("| shipping_fee | numeric (float) | |")
    lines.append("| total_amount | numeric (float) | |")
    lines.append("| shipping | nested object | `{method, region}` |")
    lines.append("")

    # --- status distribution -------------------------------------------
    lines.append("## `status` distribution\n")
    lines.append("```")
    for v, n in Counter(r.get("status") for r in data).most_common():
        lines.append(f"{v}: {n}")
    lines.append("```\n")

    # --- timestamp parse check -----------------------------------------
    bad = sum(
        1 for r in data
        if not _is_iso(r.get("order_timestamp"))
    )
    lines.append("## `order_timestamp` parse check\n")
    lines.append(f"Timestamps failing ISO parse: {bad}\n")

    # --- downstream representation -------------------------------------
    lines.append("## Representing `shipping` downstream\n")
    lines.append(DOWNSTREAM_REPRESENTATION)
    lines.append("")

    # --- validation rules ----------------------------------------------
    lines.append("## Candidate validation rules\n")
    for i, rule in enumerate(VALIDATION_RULES, start=1):
        lines.append(f"{i}. {rule}")
    lines.append("")

    # --- scope note -----------------------------------------------------
    lines.append("## Scope note\n")
    lines.append(SCOPE_NOTE)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


def _is_iso(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    main()