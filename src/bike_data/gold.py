"""Deterministic analytical Gold models built from Silver Parquet tables."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

GOLD_TABLES = (
    "dim_date",
    "dim_station",
    "dim_vehicle_type",
    "dim_region",
    "dim_pricing_plan",
    "dim_pricing_plan_tier",
    "fact_station_availability",
    "fact_station_vehicle_type_availability",
    "fact_free_bike_snapshot",
    "gold_system_availability",
    "gold_station_availability_metrics",
)

TEMPORAL_JOIN_TOLERANCE = timedelta(minutes=5)

_BASE = {
    "observed_at": pa.timestamp("us"),
}

GOLD_SCHEMAS = {
    "dim_date": pa.schema(
        {
            "date_key": pa.int64(),
            "calendar_date": pa.date32(),
            "year": pa.int64(),
            "quarter": pa.int64(),
            "month": pa.int64(),
            "week": pa.int64(),
            "day_of_week": pa.int64(),
            "day_name": pa.string(),
            "is_weekend": pa.bool_(),
        }
    ),
    "dim_station": pa.schema(
        {
            "station_id": pa.string(),
            **_BASE,
            "name": pa.string(),
            "short_name": pa.string(),
            "lat": pa.float64(),
            "lon": pa.float64(),
            "region_id": pa.string(),
            "capacity": pa.int64(),
            "is_virtual_station": pa.bool_(),
        }
    ),
    "dim_vehicle_type": pa.schema(
        {
            "vehicle_type_id": pa.string(),
            **_BASE,
            "name": pa.string(),
            "form_factor": pa.string(),
            "propulsion_type": pa.string(),
            "rider_capacity": pa.int64(),
            "max_range_meters": pa.int64(),
            "is_ebike": pa.bool_(),
        }
    ),
    "dim_region": pa.schema({"region_id": pa.string(), **_BASE, "name": pa.string()}),
    "dim_pricing_plan": pa.schema(
        {
            "plan_id": pa.string(),
            **_BASE,
            "name": pa.string(),
            "currency": pa.string(),
            "price": pa.float64(),
            "is_taxable": pa.bool_(),
            "description": pa.string(),
        }
    ),
    "dim_pricing_plan_tier": pa.schema(
        {
            "plan_id": pa.string(),
            "tier_index": pa.int64(),
            **_BASE,
            "start": pa.int64(),
            "interval": pa.int64(),
            "rate": pa.float64(),
            "end": pa.int64(),
        }
    ),
    "fact_station_availability": pa.schema(
        {
            "station_id": pa.string(),
            **_BASE,
            "date_key": pa.int64(),
            "hour_of_day": pa.int64(),
            "region_id": pa.string(),
            "capacity": pa.int64(),
            "num_bikes_available": pa.int64(),
            "num_docks_available": pa.int64(),
            "is_installed": pa.bool_(),
            "is_renting": pa.bool_(),
            "is_returning": pa.bool_(),
            "last_reported": pa.int64(),
        }
    ),
    "fact_station_vehicle_type_availability": pa.schema(
        {
            "station_id": pa.string(),
            "vehicle_type_id": pa.string(),
            **_BASE,
            "date_key": pa.int64(),
            "hour_of_day": pa.int64(),
            "count": pa.int64(),
            "is_ebike": pa.bool_(),
        }
    ),
    "fact_free_bike_snapshot": pa.schema(
        {
            "bike_id": pa.string(),
            **_BASE,
            "date_key": pa.int64(),
            "hour_of_day": pa.int64(),
            "station_id": pa.string(),
            "vehicle_type_id": pa.string(),
            "pricing_plan_id": pa.string(),
            "lat": pa.float64(),
            "lon": pa.float64(),
            "is_reserved": pa.bool_(),
            "is_disabled": pa.bool_(),
            "current_fuel_percent": pa.float64(),
            "current_range_meters": pa.int64(),
        }
    ),
    "gold_system_availability": pa.schema(
        {
            "observed_at": pa.timestamp("us"),
            "date_key": pa.int64(),
            "hour_of_day": pa.int64(),
            "station_count": pa.int64(),
            "total_capacity": pa.int64(),
            "total_bikes_available": pa.int64(),
            "total_docks_available": pa.int64(),
            "total_ebikes_available": pa.int64(),
            "ebike_share_of_available_bikes": pa.float64(),
        }
    ),
    "gold_station_availability_metrics": pa.schema(
        {
            "station_id": pa.string(),
            "snapshot_count": pa.int64(),
            "average_bikes_available": pa.float64(),
            "minimum_bikes_available": pa.int64(),
            "maximum_bikes_available": pa.int64(),
            "empty_snapshot_count": pa.int64(),
            "average_availability_ratio": pa.float64(),
        }
    ),
}


def transform_silver_to_gold(silver_root: Path, gold_root: Path) -> dict[str, Path]:
    """Build deterministic Gold tables from Silver table Parquet files."""
    silver = {
        name: pq.read_table(silver_root / f"{name}.parquet").to_pylist()
        for name in (
            "station_information",
            "station_status",
            "station_status_vehicle_types",
            "vehicle_types",
            "system_regions",
            "system_pricing_plans",
            "system_pricing_plan_tiers",
            "free_bike_status",
        )
    }
    station_info = _index(silver["station_information"], "station_id")
    vehicle_types = _index(silver["vehicle_types"], "vehicle_type_id")
    regions = _index(silver["system_regions"], "region_id")
    pricing_plans = _index(silver["system_pricing_plans"], "plan_id")

    station_facts = []
    for status in silver["station_status"]:
        key = _snapshot_key(status, "station_id")
        info = _required_snapshot(station_info, key, "station_information")
        if info["region_id"] is not None:
            _required_snapshot(
                regions,
                _snapshot_key(info, "region_id"),
                "system_regions",
            )
        station_facts.append(
            {
                "station_id": status["station_id"],
                "observed_at": status["observed_at"],
                **_time_keys(status["observed_at"]),
                "region_id": info["region_id"],
                "capacity": info["capacity"],
                "num_bikes_available": status["num_bikes_available"],
                "num_docks_available": status["num_docks_available"],
                "is_installed": status["is_installed"],
                "is_renting": status["is_renting"],
                "is_returning": status["is_returning"],
                "last_reported": status["last_reported"],
            }
        )

    vehicle_facts = []
    for row in silver["station_status_vehicle_types"]:
        vehicle = _required_snapshot(
            vehicle_types,
            _snapshot_key(row, "vehicle_type_id"),
            "vehicle_types",
        )
        vehicle_facts.append(
            {
                "station_id": row["station_id"],
                "vehicle_type_id": row["vehicle_type_id"],
                "observed_at": row["observed_at"],
                **_time_keys(row["observed_at"]),
                "count": row["count"],
                "is_ebike": _is_ebike(vehicle),
            }
        )

    free_bike_facts = []
    for row in silver["free_bike_status"]:
        if row["station_id"] is not None:
            _required_snapshot(
                station_info,
                _snapshot_key(row, "station_id"),
                "station_information",
            )
        _required_snapshot(
            vehicle_types,
            _snapshot_key(row, "vehicle_type_id"),
            "vehicle_types",
        )
        if row["pricing_plan_id"] is not None:
            _required_snapshot(
                pricing_plans,
                _snapshot_key(row, "pricing_plan_id"),
                "system_pricing_plans",
            )
        free_bike_facts.append(
            {
                "bike_id": row["bike_id"],
                "observed_at": row["observed_at"],
                **_time_keys(row["observed_at"]),
                "station_id": row["station_id"],
                "vehicle_type_id": row["vehicle_type_id"],
                "pricing_plan_id": row["pricing_plan_id"],
                "lat": row["lat"],
                "lon": row["lon"],
                "is_reserved": row["is_reserved"],
                "is_disabled": row["is_disabled"],
                "current_fuel_percent": row["current_fuel_percent"],
                "current_range_meters": row["current_range_meters"],
            }
        )

    tables = {
        "dim_date": _date_dimension(station_facts),
        "dim_station": [
            {key: row[key] for key in GOLD_SCHEMAS["dim_station"].names}
            for row in silver["station_information"]
        ],
        "dim_vehicle_type": [
            {
                **{
                    key: row[key]
                    for key in GOLD_SCHEMAS["dim_vehicle_type"].names
                    if key != "is_ebike"
                },
                "is_ebike": _is_ebike(row),
            }
            for row in silver["vehicle_types"]
        ],
        "dim_region": [
            {key: row[key] for key in GOLD_SCHEMAS["dim_region"].names}
            for row in silver["system_regions"]
        ],
        "dim_pricing_plan": [
            {key: row[key] for key in GOLD_SCHEMAS["dim_pricing_plan"].names}
            for row in silver["system_pricing_plans"]
        ],
        "dim_pricing_plan_tier": [
            {key: row[key] for key in GOLD_SCHEMAS["dim_pricing_plan_tier"].names}
            for row in silver["system_pricing_plan_tiers"]
        ],
        "fact_station_availability": station_facts,
        "fact_station_vehicle_type_availability": vehicle_facts,
        "fact_free_bike_snapshot": free_bike_facts,
    }
    tables["gold_system_availability"] = _system_metrics(station_facts, vehicle_facts)
    tables["gold_station_availability_metrics"] = _station_metrics(station_facts)

    paths = {}
    for name in GOLD_TABLES:
        rows = sorted(tables[name], key=_sort_row)
        path = gold_root / f"{name}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows, schema=GOLD_SCHEMAS[name]), path)
        paths[name] = path
    return paths


def _index(
    rows: list[dict[str, Any]], identifier: str
) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        key = _snapshot_key(row, identifier)
        candidates = result.setdefault(key[0], [])
        if any(candidate["observed_at"] == key[1] for candidate in candidates):
            raise ValueError(f"duplicate Gold dimension key: {identifier}={key}")
        candidates.append(row)
    for candidates in result.values():
        candidates.sort(key=lambda row: row["observed_at"])
    return result


def _snapshot_key(row: dict[str, Any], identifier: str) -> tuple[Any, Any]:
    return row[identifier], row["observed_at"]


def _required_snapshot(index, key, table_name):
    candidates = index.get(key[0], [])
    if not candidates:
        raise ValueError(f"missing temporal foreign key in {table_name}: {key}")
    distances = [abs(row["observed_at"] - key[1]) for row in candidates]
    nearest_distance = min(distances)
    if nearest_distance > TEMPORAL_JOIN_TOLERANCE:
        raise ValueError(
            f"temporal foreign key outside tolerance in {table_name}: {key}"
        )
    if distances.count(nearest_distance) > 1:
        raise ValueError(f"ambiguous temporal foreign key in {table_name}: {key}")
    match = candidates[distances.index(nearest_distance)]
    return match


def _time_keys(observed_at: datetime) -> dict[str, int]:
    return {
        "date_key": int(observed_at.strftime("%Y%m%d")),
        "hour_of_day": observed_at.hour,
    }


def _is_ebike(row: dict[str, Any]) -> bool:
    return str(row.get("propulsion_type") or "").lower() in {
        "electric",
        "electric_assist",
    }


def _date_dimension(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = {row["observed_at"].date() for row in rows}
    return [
        {
            "date_key": int(day.strftime("%Y%m%d")),
            "calendar_date": day,
            "year": day.year,
            "quarter": (day.month - 1) // 3 + 1,
            "month": day.month,
            "week": day.isocalendar().week,
            "day_of_week": day.isoweekday(),
            "day_name": day.strftime("%A"),
            "is_weekend": day.isoweekday() >= 6,
        }
        for day in sorted(dates)
    ]


def _system_metrics(station_rows, vehicle_rows):
    grouped = {}
    for row in station_rows:
        group = grouped.setdefault(row["observed_at"], [])
        group.append(row)
    ebikes = {}
    for row in vehicle_rows:
        if row["is_ebike"]:
            ebikes[row["observed_at"]] = (
                ebikes.get(row["observed_at"], 0) + row["count"]
            )
    metrics = []
    for observed_at, rows in grouped.items():
        total_bikes = sum(row["num_bikes_available"] or 0 for row in rows)
        metrics.append(
            {
                "observed_at": observed_at,
                **_time_keys(observed_at),
                "station_count": len(rows),
                "total_capacity": _sum_nullable(rows, "capacity"),
                "total_bikes_available": total_bikes,
                "total_docks_available": sum(
                    row["num_docks_available"] or 0 for row in rows
                ),
                "total_ebikes_available": ebikes.get(observed_at, 0),
                "ebike_share_of_available_bikes": (
                    ebikes.get(observed_at, 0) / total_bikes if total_bikes else None
                ),
            }
        )
    return metrics


def _station_metrics(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row["station_id"], []).append(row)
    result = []
    for station_id, values in grouped.items():
        bikes = [row["num_bikes_available"] for row in values]
        ratios = [
            row["num_bikes_available"] / row["capacity"]
            for row in values
            if row["capacity"] not in (None, 0)
        ]
        result.append(
            {
                "station_id": station_id,
                "snapshot_count": len(values),
                "average_bikes_available": sum(bikes) / len(bikes),
                "minimum_bikes_available": min(bikes),
                "maximum_bikes_available": max(bikes),
                "empty_snapshot_count": sum(value == 0 for value in bikes),
                "average_availability_ratio": (
                    sum(ratios) / len(ratios) if ratios else None
                ),
            }
        )
    return result


def _sum_nullable(rows, key):
    values = [row[key] for row in rows if row[key] is not None]
    return sum(values) if values else None


def _sort_row(row):
    return tuple(
        str(row.get(key, ""))
        for key in (
            "observed_at",
            "station_id",
            "vehicle_type_id",
            "bike_id",
            "plan_id",
            "tier_index",
        )
    )
