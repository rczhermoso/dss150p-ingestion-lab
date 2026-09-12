"""
Profile data/customers.csv and write a reproducible evidence report.

Outputs:
    outputs/profiling_customers.md

Design notes:
- Reads the source as-is. Never mutates or repairs records.
- All numeric findings are generated from the source on each run,
  so the report is reproducible when the source is unchanged.
"""

import os
from pathlib import Path

import pandas as pd

SRC = Path("data/customers.csv")
OUT = Path("outputs/profiling_customers.md")

# Columns whose logical type should be asserted regardless of CSV text storage.
LOGICAL_TYPES = [
    ("customer_id",       "string (identifier)", "Opaque ID; not unique in source"),
    ("first_name",        "string",              "Free-text"),
    ("last_name",         "string",              "Free-text"),
    ("email",             "string (nullable)",   "See null counts"),
    ("city",              "string (nullable)",   "See null counts"),
    ("signup_date",       "date",                "Stored as text in CSV"),
    ("customer_segment",  "string (categorical)", "Enumerated below"),
]

VALIDATION_RULES = [
    "`customer_id` — required; must be unique. **Source violates this.**",
    "`email` — if present, must match a basic address pattern "
    "(`^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$`).",
    "`signup_date` — required; must parse as ISO date; must not be in the future.",
    "`customer_segment` — must be one of the values observed below.",
    "`first_name` / `last_name` — required; non-empty strings.",
]

SCOPE_NOTE = (
    "No source records were removed or repaired. "
    "All findings are documented only, per the lab's engineering constraints."
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(SRC)
    lines: list[str] = []

    # --- Header ---------------------------------------------------------
    lines.append("# Profiling: customers.csv\n")
    lines.append(f"- File size: {os.path.getsize(SRC)} bytes")
    lines.append(f"- Shape: {df.shape[0]} rows x {df.shape[1]} columns\n")

    # --- Column dtypes as read -----------------------------------------
    lines.append("## dtypes as read by pandas\n")
    lines.append("```")
    lines.append(df.dtypes.to_string())
    lines.append("```\n")

    # --- Logical types --------------------------------------------------
    lines.append("## Logical types\n")
    lines.append("| Column | Logical type | Notes |")
    lines.append("|---|---|---|")
    for name, logical, note in LOGICAL_TYPES:
        lines.append(f"| {name} | {logical} | {note} |")
    lines.append("")

    # --- Null counts ----------------------------------------------------
    lines.append("## Nulls per column\n")
    lines.append("```")
    lines.append(df.isna().sum().to_string())
    lines.append("```\n")

    # --- Exact duplicates ----------------------------------------------
    dup_count = int(df.duplicated().sum())
    lines.append("## Exact duplicate rows\n")
    lines.append(f"Count: {dup_count}\n")

    # --- customer_id uniqueness ----------------------------------------
    dup_series = df["customer_id"].value_counts()
    dup_series = dup_series[dup_series > 1]
    lines.append("## customer_id uniqueness\n")
    lines.append(f"Duplicate occurrences: {int(df['customer_id'].duplicated().sum())}")
    lines.append(f"Distinct IDs affected: {len(dup_series)}\n")
    if len(dup_series):
        lines.append("```")
        lines.append(dup_series.to_string())
        lines.append("```")
    lines.append("")

    # --- customer_segment distribution ---------------------------------
    lines.append("## customer_segment distribution\n")
    lines.append("```")
    lines.append(df["customer_segment"].value_counts(dropna=False).to_string())
    lines.append("```\n")

    # --- signup_date parse check ---------------------------------------
    lines.append("## signup_date parse check\n")
    try:
        parsed = pd.to_datetime(df["signup_date"], errors="raise")
        lines.append(f"All {len(parsed)} values parse as dates.")
        lines.append(f"Range: {parsed.min().date()} to {parsed.max().date()}\n")
    except Exception as exc:
        lines.append(f"Parse failure: {exc}\n")

    # --- Candidate validation rules ------------------------------------
    lines.append("## Candidate validation rules\n")
    for i, rule in enumerate(VALIDATION_RULES, start=1):
        lines.append(f"{i}. {rule}")
    lines.append("")

    # --- Scope note -----------------------------------------------------
    lines.append("## Scope note\n")
    lines.append(SCOPE_NOTE)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()