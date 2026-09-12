"""Transform Silver Parquet tables into deterministic Gold tables."""

from pathlib import Path

from bike_data.gold import transform_silver_to_gold

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    paths = transform_silver_to_gold(root / "data" / "silver", root / "data" / "gold")
    for name, path in paths.items():
        print(f"{name}: {path}")
