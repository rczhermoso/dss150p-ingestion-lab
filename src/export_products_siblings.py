"""Generate CSV and JSON siblings from products.parquet for size/type comparison."""

from pathlib import Path
import pandas as pd

OUT = Path("outputs")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet("data/products.parquet")
df.to_csv(OUT / "products_as_csv.csv", index=False)
df.to_json(OUT / "products_as_json.json", orient="records", indent=2)

print(f"Wrote {OUT / 'products_as_csv.csv'}")
print(f"Wrote {OUT / 'products_as_json.json'}")