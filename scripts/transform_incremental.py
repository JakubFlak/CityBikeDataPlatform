"""Run the restartable Raw -> Silver -> Gold pipeline incrementally."""

from pathlib import Path

from bike_data.incremental import (
    incremental_raw_to_silver,
    incremental_silver_to_gold,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    incremental_raw_to_silver(root / "data" / "raw", root / "data" / "silver")
    paths = incremental_silver_to_gold(root / "data" / "silver", root / "data" / "gold")
    for table_name, path in paths.items():
        print(f"{table_name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
