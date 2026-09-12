import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from bike_data.silver import SILVER_TABLES, TABLE_SCHEMAS, transform_raw_to_silver


def write_raw_snapshot(
    raw_root: Path, feed_name: str, observed_at: datetime, data: dict
):
    payload = {
        "last_updated": int(observed_at.timestamp()),
        "ttl": 60,
        "version": "2.3",
        "data": data,
    }
    row = {
        "feed_name": feed_name,
        "source_url": f"https://example.test/{feed_name}.json",
        "observed_at": observed_at.isoformat(),
        "last_updated": payload["last_updated"],
        "ttl": payload["ttl"],
        "version": payload["version"],
        "data_json": json.dumps(data),
        "source_payload_json": json.dumps(payload),
    }
    path = (
        raw_root
        / feed_name
        / f"{observed_at.strftime('%Y%m%dT%H%M%S')}"
        / "snapshot.parquet"
    )
    path.parent.mkdir(parents=True)
    pq.write_table(pa.table({key: [value] for key, value in row.items()}), path)


def populate_raw(raw_root: Path):
    first = datetime(2026, 9, 12, 10, tzinfo=UTC)
    second = datetime(2026, 9, 12, 10, 1, tzinfo=UTC)
    for timestamp in (first, second):
        write_raw_snapshot(
            raw_root,
            "vehicle_types",
            timestamp,
            {"vehicle_types": [{"vehicle_type_id": "71", "name": "Bike"}]},
        )
        write_raw_snapshot(
            raw_root,
            "station_information",
            timestamp,
            {
                "stations": [
                    {
                        "station_id": "S1",
                        "name": "Station",
                        "lat": 51.1,
                        "lon": 17.0,
                        "rental_uris": {"web": "https://example.test/station"},
                    }
                ]
            },
        )
        write_raw_snapshot(
            raw_root,
            "station_status",
            timestamp,
            {
                "stations": [
                    {
                        "station_id": "S1",
                        "num_bikes_available": 2,
                        "num_docks_available": 3,
                        "vehicle_types_available": [
                            {"vehicle_type_id": "71", "count": 2}
                        ],
                    }
                ]
            },
        )
        write_raw_snapshot(
            raw_root,
            "free_bike_status",
            timestamp,
            {
                "bikes": [
                    {
                        "bike_id": f"B{timestamp.minute}",
                        "station_id": "S1",
                        "vehicle_type_id": "71",
                        "lat": 51.1,
                        "lon": 17.0,
                        "rental_uris": {"web": "https://example.test/bike"},
                    }
                ]
            },
        )
        write_raw_snapshot(
            raw_root,
            "system_pricing_plans",
            timestamp,
            {
                "plans": [
                    {
                        "plan_id": "P1",
                        "name": "Basic",
                        "currency": "PLN",
                        "price": 0,
                        "per_min_pricing": [
                            {"start": 20, "interval": 40, "rate": 3, "end": 60}
                        ],
                    }
                ]
            },
        )
        write_raw_snapshot(
            raw_root,
            "system_regions",
            timestamp,
            {"regions": [{"region_id": "148", "name": "Wroclaw"}]},
        )


def read_table(paths, name):
    return pq.read_table(paths[name])


def test_silver_writes_all_expected_tables_and_schemas(tmp_path):
    raw_root = tmp_path / "raw"
    populate_raw(raw_root)

    paths = transform_raw_to_silver(raw_root, tmp_path / "silver")

    assert tuple(paths) == SILVER_TABLES
    assert set(paths) == set(SILVER_TABLES)
    for table_name in SILVER_TABLES:
        table = read_table(paths, table_name)
        assert table.schema == TABLE_SCHEMAS[table_name]


def test_silver_preserves_snapshot_grain_and_nested_relationships(tmp_path):
    raw_root = tmp_path / "raw"
    populate_raw(raw_root)
    paths = transform_raw_to_silver(raw_root, tmp_path / "silver")

    station_status = read_table(paths, "station_status").to_pylist()
    availability = read_table(paths, "station_status_vehicle_types").to_pylist()
    pricing_tiers = read_table(paths, "system_pricing_plan_tiers").to_pylist()

    assert len(station_status) == 2
    assert len({(row["station_id"], row["observed_at"]) for row in station_status}) == 2
    assert len(availability) == 2
    assert all(row["count"] == 2 for row in availability)
    assert all(
        (row["station_id"], row["observed_at"])
        in {(parent["station_id"], parent["observed_at"]) for parent in station_status}
        for row in availability
    )
    assert len(pricing_tiers) == 2
    assert all(row["tier_index"] == 0 for row in pricing_tiers)

    station_info = read_table(paths, "station_information").to_pylist()[0]
    assert json.loads(station_info["rental_uris_json"]) == {
        "web": "https://example.test/station"
    }


def test_silver_keys_are_unique_and_lineage_is_preserved(tmp_path):
    raw_root = tmp_path / "raw"
    populate_raw(raw_root)
    paths = transform_raw_to_silver(raw_root, tmp_path / "silver")

    key_columns = {
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
        "system_pricing_plan_tiers": ("plan_id", "tier_index", "observed_at"),
        "system_regions": ("region_id", "observed_at"),
    }
    for table_name, columns in key_columns.items():
        rows = read_table(paths, table_name).to_pylist()
        keys = [tuple(row[column] for column in columns) for row in rows]
        assert len(keys) == len(set(keys))
        assert all(row["feed_name"] for row in rows)
        assert all(row["source_url"] for row in rows)
        assert all(row["observed_at"].tzinfo is None for row in rows)


def test_silver_transformation_is_repeatable(tmp_path):
    raw_root = tmp_path / "raw"
    populate_raw(raw_root)
    first_paths = transform_raw_to_silver(raw_root, tmp_path / "silver_one")
    second_paths = transform_raw_to_silver(raw_root, tmp_path / "silver_two")

    for table_name in SILVER_TABLES:
        first = read_table(first_paths, table_name)
        second = read_table(second_paths, table_name)
        assert first.schema == second.schema
        assert first.to_pylist() == second.to_pylist()
