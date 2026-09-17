"""Validate the Gold schema before publishing pipeline artifacts."""

import sys
from pathlib import Path

import pyarrow.parquet as pq

from bike_data.gold import GOLD_SCHEMAS, GOLD_TABLES


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/gold")
    failures = []
    for name in GOLD_TABLES:
        path = root / f"{name}.parquet"
        if not path.exists():
            failures.append(f"missing Gold table: {path}")
            continue
        actual = pq.read_schema(path)
        expected = GOLD_SCHEMAS[name]
        if actual != expected:
            failures.append(f"schema mismatch: {path}")
        if "observed_at" in expected.names and "observed_at_local" not in actual.names:
            failures.append(f"missing observed_at_local: {path}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(f"Gold schema valid: {len(GOLD_TABLES)} tables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
