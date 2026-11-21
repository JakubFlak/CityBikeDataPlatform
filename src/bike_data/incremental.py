
"""Restartable incremental processing for the local Raw, Silver, and Gold layers."""

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from bike_data.gold import GOLD_SCHEMAS, GOLD_TABLES, transform_silver_to_gold
from bike_data.silver import (
    SILVER_TABLES,
    TABLE_SCHEMAS,
    _append_snapshot_records,
)

DEFAULT_STATE_PATH = "_incremental_state.json"

SILVER_KEYS = {
    "vehicle_types": ("vehicle_type_id", "observed_at"),
    "station_information": ("station_id", "observed_at"),
    "station_status": ("station_id", "observed_at"),
    "station_status_vehicle_types": (
        "station_id",
        "vehicle_type_id",
        "observed_at",
    ),
    "free_bike_status": ("bike_id", "observed_at"),
    "system_pricing_plans": ("plan_id", "observed_at"),
    "system_pricing_plan_tiers": (
        "plan_id",
        "tier_index",
        "observed_at",
    ),
    "system_regions": ("region_id", "observed_at"),
}

# Maps each GBFS feed to the Silver tables it can affect.
SILVER_FEED_TABLES = {
    "vehicle_types": {"vehicle_types"},
    "station_information": {"station_information"},
    "station_status": {
        "station_status",
        "station_status_vehicle_types",
    },
    "free_bike_status": {"free_bike_status"},
    "system_pricing_plans": {
        "system_pricing_plans",
        "system_pricing_plan_tiers",
    },
    "system_regions": {"system_regions"},
}


def incremental_raw_to_silver(
    raw_root: Path,
    silver_root: Path,
    state_path: Path | None = None,
    on_snapshot: Callable[[Path], None] | None = None,
) -> dict[str, Path]:
    """Process unseen Raw snapshots and update only affected Silver tables.

    The state file is written only after all affected Silver files are committed.
    If processing fails, pending snapshots are retried on the next run.
    """
    state_path = state_path or silver_root / DEFAULT_STATE_PATH
    state = _read_state(state_path)

    raw_paths = sorted(raw_root.glob("**/*.parquet"))
    snapshots = [_snapshot_metadata(path) for path in raw_paths]
    _validate_snapshot_metadata(snapshots)

    known = state.setdefault("raw_snapshots", {})
    pending = []

    for snapshot in snapshots:
        identity = snapshot["identity"]

        if identity not in known:
            pending.append(snapshot)
        elif known[identity]["payload_hash"] != snapshot["payload_hash"]:
            raise ValueError(f"raw snapshot content changed: {identity}")

    # Identify only the Silver tables affected by pending Raw snapshots.
    affected_tables = set()

    for snapshot in pending:
        feed_name = snapshot["feed_name"]
        affected = SILVER_FEED_TABLES.get(feed_name)

        if affected is None:
            raise ValueError(
                f"no Silver table mapping configured for GBFS feed: {feed_name}"
            )

        affected_tables.update(affected)

        if on_snapshot is not None:
            on_snapshot(snapshot["path"])

    # Keep the full records dictionary because _append_snapshot_records()
    # expects all Silver table names to be available.
    records = {table: [] for table in SILVER_TABLES}

    for snapshot in pending:
        _append_snapshot_records(records, snapshot["path"])

    # Preserve the existing initialization behavior: create any missing
    # Silver files, even when there are no new Raw snapshots.
    missing_tables = {
        name
        for name in SILVER_TABLES
        if not (silver_root / f"{name}.parquet").exists()
    }

    tables_to_write = affected_tables | missing_tables

    if tables_to_write:
        combined = {}

        for table_name in SILVER_TABLES:
            if table_name not in tables_to_write:
                continue

            existing = _read_existing(
                silver_root / f"{table_name}.parquet"
            )

            combined[table_name] = _merge_rows(
                existing + records[table_name],
                SILVER_KEYS[table_name],
            )

        _commit_parquet_tables(silver_root, combined)

    # Mark snapshots as Silver-processed only after all affected files
    # have been successfully committed.
    if pending:
        for snapshot in pending:
            known[snapshot["identity"]] = {
                "payload_hash": snapshot["payload_hash"],
                "source_url": snapshot["source_url"],
                "status": "silver_complete",
            }

        _write_state(state_path, state)

    elif missing_tables:
        _write_state(state_path, state)

    return {
        name: silver_root / f"{name}.parquet"
        for name in SILVER_TABLES
    }



def incremental_silver_to_gold(
    silver_root: Path,
    gold_root: Path,
) -> dict[str, Path]:
    """Rebuild Gold and publish validated Parquet files."""
    gold_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=gold_root.parent) as temporary:
        candidate_root = Path(temporary)

        candidate = transform_silver_to_gold(
            silver_root,
            candidate_root,
        )

        # Validate every candidate before replacing any existing Gold file.
        _validate_gold_candidate(candidate)

        # The temporary directory is created under gold_root.parent,
        # so candidate and destination are on the same filesystem.
        # os.replace publishes each already-written Parquet file directly.
        for name in GOLD_TABLES:
            os.replace(
                candidate[name],
                gold_root / f"{name}.parquet",
            )

    return {
        name: gold_root / f"{name}.parquet"
        for name in GOLD_TABLES
    }



def _snapshot_metadata(path: Path) -> dict[str, Any]:
    row = pq.ParquetFile(path).read().to_pylist()[0]
    observed_at = row["observed_at"]
    feed_name = row["feed_name"]
    identity = f"{feed_name}|{observed_at}"
    payload_hash = hashlib.sha256(
        row["data_json"].encode("utf-8")
    ).hexdigest()

    return {
        "path": path,
        "feed_name": feed_name,
        "identity": identity,
        "payload_hash": payload_hash,
        "source_url": row["source_url"],
    }


def _validate_snapshot_metadata(
    snapshots: list[dict[str, Any]],
) -> None:
    seen = {}

    for snapshot in snapshots:
        identity = snapshot["identity"]
        prior = seen.get(identity)

        if prior is not None and prior["payload_hash"] != snapshot["payload_hash"]:
            raise ValueError(
                f"conflicting raw snapshot identity: {identity}"
            )

        seen[identity] = snapshot


def _read_existing(path: Path) -> list[dict[str, Any]]:
    return (
        pq.ParquetFile(path).read().to_pylist()
        if path.exists()
        else []
    )


def _validate_gold_candidate(candidate: dict[str, Path]) -> None:
    missing = [
        name for name in GOLD_TABLES
        if name not in candidate
    ]

    if missing:
        raise ValueError(
            f"Gold candidate is missing tables: {', '.join(missing)}"
        )

    for name in GOLD_TABLES:
        path = candidate[name]

        if not path.exists():
            raise ValueError(f"Gold candidate is missing file: {path}")

        if pq.read_schema(path) != GOLD_SCHEMAS[name]:
            raise ValueError(f"Gold candidate schema mismatch: {path}")


def _merge_rows(
    rows: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    merged = {}

    for row in rows:
        key = tuple(row[key_name] for key_name in keys)
        prior = merged.get(key)

        if prior is not None and prior != row:
            raise ValueError(f"conflicting row for key {key}")

        merged[key] = row

    return sorted(merged.values(), key=_row_sort_key)


def _row_sort_key(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(row.get(key, ""))
        for key in (
            "observed_at",
            "station_id",
            "vehicle_type_id",
            "bike_id",
            "plan_id",
            "region_id",
            "tier_index",
            "date_key",
        )
    )


def _commit_parquet_tables(
    root: Path,
    rows_by_table: dict[str, list[dict[str, Any]]],
    schemas_from: dict[str, Path] | None = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=".incremental-", dir=root)
    )

    try:
        for name, rows in rows_by_table.items():
            source = (
                schemas_from[name]
                if schemas_from
                else root / f"{name}.parquet"
            )

            if source.exists():
                schema = pq.read_schema(source)

                if name in GOLD_SCHEMAS:
                    schema = GOLD_SCHEMAS[name]
            else:
                schema = (
                    TABLE_SCHEMAS[name]
                    if name in TABLE_SCHEMAS
                    else GOLD_SCHEMAS[name]
                )

            table = pa.Table.from_pylist(rows, schema=schema)
            path = staging / f"{name}.parquet"
            pq.write_table(table, path)

        for name in rows_by_table:
            os.replace(
                staging / f"{name}.parquet",
                root / f"{name}.parquet",
            )

    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"raw_snapshots": {}}

    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")

    temporary.write_text(
        json.dumps(
            state,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    os.replace(temporary, path)


def mark_snapshots_complete(
    silver_root: Path,
    identities: set[str],
) -> None:
    """Mark Silver-processed snapshots complete after downstream success."""

    state_path = silver_root / DEFAULT_STATE_PATH
    state = _read_state(state_path)
    known = state.setdefault("raw_snapshots", {})

    for identity in identities:
        if identity in known:
            known[identity]["status"] = "complete"

    _write_state(state_path, state)
