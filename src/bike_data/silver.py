"""Deterministic transformation from raw GBFS JSON to Silver Parquet tables."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

SILVER_TABLES = (
    "vehicle_types",
    "station_information",
    "station_status",
    "station_status_vehicle_types",
    "free_bike_status",
    "system_pricing_plans",
    "system_pricing_plan_tiers",
    "system_regions",
)

_BASE_COLUMNS = {
    "feed_name": pa.string(),
    "source_url": pa.string(),
    # Values are normalized to UTC before writing. The physical type is
    # timezone-naive for portable reads with the project's pyarrow runtime.
    "observed_at": pa.timestamp("us"),
    "last_updated": pa.int64(),
}

TABLE_SCHEMAS = {
    "vehicle_types": pa.schema(
        {
            **_BASE_COLUMNS,
            "vehicle_type_id": pa.string(),
            "name": pa.string(),
            "form_factor": pa.string(),
            "propulsion_type": pa.string(),
            "rider_capacity": pa.int64(),
            "max_range_meters": pa.int64(),
            "vehicle_image": pa.string(),
            "description": pa.string(),
        }
    ),
    "station_information": pa.schema(
        {
            **_BASE_COLUMNS,
            "station_id": pa.string(),
            "name": pa.string(),
            "short_name": pa.string(),
            "lat": pa.float64(),
            "lon": pa.float64(),
            "region_id": pa.string(),
            "capacity": pa.int64(),
            "is_virtual_station": pa.bool_(),
            "rental_uris_json": pa.string(),
        }
    ),
    "station_status": pa.schema(
        {
            **_BASE_COLUMNS,
            "station_id": pa.string(),
            "last_reported": pa.int64(),
            "num_bikes_available": pa.int64(),
            "num_docks_available": pa.int64(),
            "is_installed": pa.bool_(),
            "is_renting": pa.bool_(),
            "is_returning": pa.bool_(),
        }
    ),
    "station_status_vehicle_types": pa.schema(
        {
            **_BASE_COLUMNS,
            "station_id": pa.string(),
            "vehicle_type_id": pa.string(),
            "count": pa.int64(),
        }
    ),
    "free_bike_status": pa.schema(
        {
            **_BASE_COLUMNS,
            "bike_id": pa.string(),
            "station_id": pa.string(),
            "vehicle_type_id": pa.string(),
            "pricing_plan_id": pa.string(),
            "lat": pa.float64(),
            "lon": pa.float64(),
            "is_reserved": pa.bool_(),
            "is_disabled": pa.bool_(),
            "current_fuel_percent": pa.float64(),
            "current_range_meters": pa.int64(),
            "rental_uris_json": pa.string(),
        }
    ),
    "system_pricing_plans": pa.schema(
        {
            **_BASE_COLUMNS,
            "plan_id": pa.string(),
            "name": pa.string(),
            "currency": pa.string(),
            "price": pa.float64(),
            "is_taxable": pa.bool_(),
            "description": pa.string(),
        }
    ),
    "system_pricing_plan_tiers": pa.schema(
        {
            **_BASE_COLUMNS,
            "plan_id": pa.string(),
            "tier_index": pa.int64(),
            "start": pa.int64(),
            "interval": pa.int64(),
            "rate": pa.float64(),
            "end": pa.int64(),
        }
    ),
    "system_regions": pa.schema(
        {
            **_BASE_COLUMNS,
            "region_id": pa.string(),
            "name": pa.string(),
        }
    ),
}


def transform_raw_to_silver(raw_root: Path, silver_root: Path) -> dict[str, Path]:
    """Transform every raw snapshot into deterministic Silver Parquet tables."""

    records = {table: [] for table in SILVER_TABLES}
    for path in sorted(raw_root.glob("**/*.parquet")):
        _append_snapshot_records(records, path)

    paths: dict[str, Path] = {}
    for table_name in SILVER_TABLES:
        table_records = sorted(records[table_name], key=_sort_record)
        table_path = silver_root / f"{table_name}.parquet"
        table_path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(table_records, schema=TABLE_SCHEMAS[table_name])
        pq.write_table(table, table_path)
        paths[table_name] = table_path
    return paths


def _append_snapshot_records(
    records: dict[str, list[dict[str, Any]]], path: Path
) -> None:
    raw_table = pq.read_table(path)
    for row in raw_table.to_pylist():
        feed_name = row["feed_name"]
        observed_at = _parse_observed_at(row["observed_at"])
        lineage = {
            "feed_name": feed_name,
            "source_url": row["source_url"],
            "observed_at": observed_at,
            "last_updated": row["last_updated"],
        }
        data = json.loads(row["data_json"])
        if feed_name == "vehicle_types":
            for item in data["vehicle_types"]:
                records[feed_name].append(
                    {
                        **lineage,
                        "vehicle_type_id": item.get("vehicle_type_id"),
                        "name": item.get("name"),
                        "form_factor": item.get("form_factor"),
                        "propulsion_type": item.get("propulsion_type"),
                        "rider_capacity": item.get("rider_capacity"),
                        "max_range_meters": item.get("max_range_meters"),
                        "vehicle_image": item.get("vehicle_image"),
                        "description": item.get("_description"),
                    }
                )
        elif feed_name == "station_information":
            for item in data["stations"]:
                records[feed_name].append(
                    {
                        **lineage,
                        "station_id": item.get("station_id"),
                        "name": item.get("name"),
                        "short_name": item.get("short_name"),
                        "lat": item.get("lat"),
                        "lon": item.get("lon"),
                        "region_id": item.get("region_id"),
                        "capacity": item.get("capacity"),
                        "is_virtual_station": item.get("is_virtual_station"),
                        "rental_uris_json": _json_text(item.get("rental_uris")),
                    }
                )
        elif feed_name == "station_status":
            for item in data["stations"]:
                records[feed_name].append(
                    {
                        **lineage,
                        "station_id": item.get("station_id"),
                        "last_reported": item.get("last_reported"),
                        "num_bikes_available": item.get("num_bikes_available"),
                        "num_docks_available": item.get("num_docks_available"),
                        "is_installed": item.get("is_installed"),
                        "is_renting": item.get("is_renting"),
                        "is_returning": item.get("is_returning"),
                    }
                )
                for available in item.get("vehicle_types_available") or []:
                    records["station_status_vehicle_types"].append(
                        {
                            **lineage,
                            "station_id": item.get("station_id"),
                            "vehicle_type_id": available.get("vehicle_type_id"),
                            "count": available.get("count"),
                        }
                    )
        elif feed_name == "free_bike_status":
            for item in data["bikes"]:
                records[feed_name].append(
                    {
                        **lineage,
                        "bike_id": item.get("bike_id"),
                        "station_id": item.get("station_id"),
                        "vehicle_type_id": item.get("vehicle_type_id"),
                        "pricing_plan_id": item.get("pricing_plan_id"),
                        "lat": item.get("lat"),
                        "lon": item.get("lon"),
                        "is_reserved": item.get("is_reserved"),
                        "is_disabled": item.get("is_disabled"),
                        "current_fuel_percent": item.get("current_fuel_percent"),
                        "current_range_meters": item.get("current_range_meters"),
                        "rental_uris_json": _json_text(item.get("rental_uris")),
                    }
                )
        elif feed_name == "system_pricing_plans":
            for item in data["plans"]:
                records[feed_name].append(
                    {
                        **lineage,
                        "plan_id": item.get("plan_id"),
                        "name": item.get("name"),
                        "currency": item.get("currency"),
                        "price": item.get("price"),
                        "is_taxable": item.get("is_taxable"),
                        "description": item.get("description"),
                    }
                )
                for tier_index, tier in enumerate(item.get("per_min_pricing") or []):
                    records["system_pricing_plan_tiers"].append(
                        {
                            **lineage,
                            "plan_id": item.get("plan_id"),
                            "tier_index": tier_index,
                            "start": tier.get("start"),
                            "interval": tier.get("interval"),
                            "rate": tier.get("rate"),
                            "end": tier.get("end"),
                        }
                    )
        elif feed_name == "system_regions":
            for item in data["regions"]:
                records[feed_name].append(
                    {
                        **lineage,
                        "region_id": item.get("region_id"),
                        "name": item.get("name"),
                    }
                )
        else:
            raise ValueError(f"Unsupported raw feed: {feed_name}")


def _parse_observed_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("raw observed_at must be timezone-aware")
    return parsed.astimezone(UTC).replace(tzinfo=None)


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _sort_record(record: dict[str, Any]) -> tuple[str, str, str, int]:
    identifier = next(
        (
            record.get(column)
            for column in (
                "vehicle_type_id",
                "station_id",
                "bike_id",
                "plan_id",
                "region_id",
            )
            if record.get(column) is not None
        ),
        "",
    )
    return (
        record["observed_at"].isoformat(),
        str(identifier),
        str(record.get("vehicle_type_id", "")),
        int(record.get("tier_index", 0)),
    )
