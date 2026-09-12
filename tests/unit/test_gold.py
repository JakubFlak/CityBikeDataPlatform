import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from bike_data.gold import (
    GOLD_SCHEMAS,
    GOLD_TABLES,
    _index,
    _required_snapshot,
    transform_silver_to_gold,
)
from bike_data.silver import transform_raw_to_silver


def _write_raw_snapshot(raw_root: Path, feed_name: str, observed_at, data):
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
        / observed_at.strftime("%Y%m%d%H%M%S")
        / "snapshot.parquet"
    )
    path.parent.mkdir(parents=True)
    pq.write_table(pa.table({key: [value] for key, value in row.items()}), path)


def _populate_raw(raw_root):
    for minute, capacity in ((0, 5), (1, 6)):
        observed_at = datetime(2026, 9, 12, 10, minute, tzinfo=UTC)
        _write_raw_snapshot(
            raw_root,
            "vehicle_types",
            observed_at,
            {
                "vehicle_types": [
                    {
                        "vehicle_type_id": "bike",
                        "name": "Bike",
                        "propulsion_type": "human",
                    },
                    {
                        "vehicle_type_id": "ebike",
                        "name": "E-bike",
                        "propulsion_type": "electric",
                    },
                ]
            },
        )
        _write_raw_snapshot(
            raw_root,
            "station_information",
            observed_at,
            {
                "stations": [
                    {
                        "station_id": "S1",
                        "name": "Station",
                        "lat": 51.1,
                        "lon": 17.0,
                        "region_id": "R1",
                        "capacity": capacity,
                    }
                ]
            },
        )
        _write_raw_snapshot(
            raw_root,
            "station_status",
            observed_at,
            {
                "stations": [
                    {
                        "station_id": "S1",
                        "last_reported": int(observed_at.timestamp()),
                        "num_bikes_available": 2 + minute,
                        "num_docks_available": capacity - 2 - minute,
                        "is_installed": True,
                        "is_renting": True,
                        "is_returning": True,
                        "vehicle_types_available": [
                            {"vehicle_type_id": "bike", "count": 1},
                            {"vehicle_type_id": "ebike", "count": 1 + minute},
                        ],
                    }
                ]
            },
        )
        _write_raw_snapshot(
            raw_root,
            "free_bike_status",
            observed_at,
            {
                "bikes": [
                    {
                        "bike_id": f"B{minute}",
                        "station_id": "S1",
                        "vehicle_type_id": "ebike",
                        "pricing_plan_id": "P1",
                        "lat": 51.1,
                        "lon": 17.0,
                    }
                ]
            },
        )
        _write_raw_snapshot(
            raw_root,
            "system_pricing_plans",
            observed_at,
            {
                "plans": [
                    {
                        "plan_id": "P1",
                        "name": "Basic",
                        "currency": "PLN",
                        "price": 0,
                    }
                ]
            },
        )
        _write_raw_snapshot(
            raw_root,
            "system_regions",
            observed_at,
            {"regions": [{"region_id": "R1", "name": "Wroclaw"}]},
        )


def _read(paths, name):
    return pq.read_table(paths[name]).to_pylist()


def test_gold_grains_temporal_joins_and_metrics(tmp_path):
    raw_root = tmp_path / "raw"
    _populate_raw(raw_root)
    transform_raw_to_silver(raw_root, tmp_path / "silver")
    gold_paths = transform_silver_to_gold(tmp_path / "silver", tmp_path / "gold")

    for name in GOLD_TABLES:
        assert pq.read_table(gold_paths[name]).schema == GOLD_SCHEMAS[name]

    station_facts = _read(gold_paths, "fact_station_availability")
    vehicle_facts = _read(gold_paths, "fact_station_vehicle_type_availability")
    system = _read(gold_paths, "gold_system_availability")
    assert len(station_facts) == 2
    assert len({(row["station_id"], row["observed_at"]) for row in station_facts}) == 2
    assert len(vehicle_facts) == 4
    assert (
        len(
            {
                (row["station_id"], row["vehicle_type_id"], row["observed_at"])
                for row in vehicle_facts
            }
        )
        == 4
    )
    assert [row["capacity"] for row in station_facts] == [5, 6]
    assert [row["total_bikes_available"] for row in system] == [2, 3]
    assert [row["total_ebikes_available"] for row in system] == [1, 2]
    assert system[0]["ebike_share_of_available_bikes"] == 0.5


def test_gold_foreign_keys_and_determinism(tmp_path):
    raw_root = tmp_path / "raw"
    _populate_raw(raw_root)
    transform_raw_to_silver(raw_root, tmp_path / "silver")
    first = transform_silver_to_gold(tmp_path / "silver", tmp_path / "gold_one")
    second = transform_silver_to_gold(tmp_path / "silver", tmp_path / "gold_two")

    station_keys = {
        (row["station_id"], row["observed_at"])
        for row in _read(first, "dim_station")
    }
    vehicle_keys = {
        (row["vehicle_type_id"], row["observed_at"])
        for row in _read(first, "dim_vehicle_type")
    }
    assert all(
        (row["station_id"], row["observed_at"]) in station_keys
        for row in _read(first, "fact_station_availability")
    )
    assert all(
        (row["vehicle_type_id"], row["observed_at"]) in vehicle_keys
        for row in _read(first, "fact_station_vehicle_type_availability")
    )
    for name in GOLD_TABLES:
        assert _read(first, name) == _read(second, name)


def test_gold_joins_feeds_with_collection_time_jitter(tmp_path):
    raw_root = tmp_path / "raw"
    _populate_raw(raw_root)
    offsets = {
        "station_information": 1,
        "vehicle_types": 2,
        "system_regions": 3,
        "system_pricing_plans": 4,
        "free_bike_status": 5,
    }
    for feed_name, seconds in offsets.items():
        path = next((raw_root / feed_name).glob("**/snapshot.parquet"))
        table = pq.read_table(path)
        observed_at = [
            datetime.fromisoformat(value) + timedelta(seconds=seconds)
            for value in table["observed_at"].to_pylist()
        ]
        table = table.set_column(
            table.schema.get_field_index("observed_at"),
            "observed_at",
            pa.array([value.isoformat() for value in observed_at]),
        )
        pq.write_table(table, path)

    transform_raw_to_silver(raw_root, tmp_path / "silver")
    paths = transform_silver_to_gold(tmp_path / "silver", tmp_path / "gold")

    assert len(_read(paths, "fact_station_availability")) == 2
    assert len(_read(paths, "fact_free_bike_snapshot")) == 2


def test_gold_rejects_ambiguous_temporal_match():
    first = datetime(2026, 9, 12, 10, tzinfo=UTC).replace(tzinfo=None)
    second = datetime(2026, 9, 12, 10, 2, tzinfo=UTC).replace(tzinfo=None)
    target = datetime(2026, 9, 12, 10, 1, tzinfo=UTC).replace(tzinfo=None)
    index = _index(
        [
            {"station_id": "S1", "observed_at": first},
            {"station_id": "S1", "observed_at": second},
        ],
        "station_id",
    )
    with pytest.raises(ValueError, match="ambiguous temporal"):
        _required_snapshot(index, ("S1", target), "station_information")
