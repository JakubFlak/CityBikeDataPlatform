"""Transform raw GBFS snapshots into Silver Parquet tables."""

from pathlib import Path

from bike_data.silver import transform_raw_to_silver


def main() -> int:
    paths = transform_raw_to_silver(Path("data/raw"), Path("data/silver"))
    for table_name, path in paths.items():
        print(f"{table_name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
