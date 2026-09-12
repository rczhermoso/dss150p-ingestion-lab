import os
import pandas as pd

PATH = "data/customers.csv"
OUT = "outputs/profiling_customers.md"

df = pd.read_csv(PATH)

lines = []
lines.append("# Profiling: customers.csv\n")
lines.append(f"- File size: {os.path.getsize(PATH)} bytes")
lines.append(f"- Shape: {df.shape[0]} rows x {df.shape[1]} columns\n")

lines.append("## Nulls per column\n")
lines.append(df.isna().sum().to_string())
lines.append("")

lines.append("## Exact duplicate rows\n")
lines.append(f"Count: {df.duplicated().sum()}\n")

lines.append("## customer_id uniqueness\n")
dup_ids = df["customer_id"].value_counts()
dup_ids = dup_ids[dup_ids > 1]
lines.append(f"Duplicate occurrences: {df['customer_id'].duplicated().sum()}")
lines.append(f"Distinct IDs affected: {len(dup_ids)}")
lines.append(dup_ids.to_string() + "\n")

lines.append("## customer_segment distribution\n")
lines.append(df["customer_segment"].value_counts(dropna=False).to_string())

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Wrote {OUT}")