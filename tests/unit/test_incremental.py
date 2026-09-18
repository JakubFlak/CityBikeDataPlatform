from datetime import UTC, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from test_gold import _populate_raw, _write_raw_snapshot

from bike_data import incremental as incremental_module
from bike_data.gold import GOLD_SCHEMAS, GOLD_TABLES, transform_silver_to_gold
from bike_data.incremental import (
    incremental_raw_to_silver,
    incremental_silver_to_gold,
)
from bike_data.silver import transform_raw_to_silver


def _append_snapshot(raw_root, minute):
    observed_at = datetime(2026, 9, 12, 10, minute, tzinfo=UTC)
    _write_raw_snapshot(
        raw_root,
        "vehicle_types",
        observed_at,
        {"vehicle_types": [{"vehicle_type_id": "71", "name": "Bike"}]},
    )
    _write_raw_snapshot(
        raw_root,
        "station_information",
        observed_at,
        {"stations": [{"station_id": "S1", "name": "Station", "capacity": 5}]},
    )
    _write_raw_snapshot(
        raw_root,
        "station_status",
        observed_at,
        {
            "stations": [
                {
                    "station_id": "S1",
                    "num_bikes_available": minute,
                    "num_docks_available": 5 - minute,
                    "vehicle_types_available": [
                        {"vehicle_type_id": "71", "count": minute}
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
                    "vehicle_type_id": "71",
                }
            ]
        },
    )
    _write_raw_snapshot(
        raw_root,
        "system_pricing_plans",
        observed_at,
        {"plans": [{"plan_id": "P1", "name": "Basic"}]},
    )
    _write_raw_snapshot(
        raw_root,
        "system_regions",
        observed_at,
        {"regions": [{"region_id": "R1", "name": "Region"}]},
    )


def _rows(root, name):
    return pq.read_table(root / f"{name}.parquet").to_pylist()


def _write_legacy_gold(silver_root, gold_root):
    candidate_root = gold_root.parent / "candidate"
    candidate = transform_silver_to_gold(silver_root, candidate_root)
    gold_root.mkdir()
    for name in GOLD_TABLES:
        table = pq.read_table(candidate[name])
        fields = [
            field for field in GOLD_SCHEMAS[name] if field.name != "observed_at_local"
        ]
        rows = [
            {key: value for key, value in row.items() if key != "observed_at_local"}
            for row in table.to_pylist()
        ]
        pq.write_table(
            pa.Table.from_pylist(rows, schema=pa.schema(fields)),
            gold_root / f"{name}.parquet",
        )


def test_incremental_initial_and_append_are_idempotent(tmp_path):
    raw_root = tmp_path / "raw"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    _populate_raw(raw_root)

    incremental_raw_to_silver(raw_root, silver_root)
    incremental_silver_to_gold(silver_root, gold_root)
    assert len(_rows(silver_root, "station_status")) == 2
    assert len(_rows(gold_root, "fact_station_availability")) == 2

    _append_snapshot(raw_root, 2)
    incremental_raw_to_silver(raw_root, silver_root)
    incremental_silver_to_gold(silver_root, gold_root)
    assert len(_rows(silver_root, "station_status")) == 3
    assert len(_rows(gold_root, "fact_station_availability")) == 3
    assert all(
        row["available_stations"] == row["station_count"] - row["empty_station_count"]
        for row in _rows(gold_root, "gold_system_availability")
    )

    expected = {
        name: _rows(gold_root, name)
        for name in ("fact_station_availability", "gold_system_availability")
    }
    incremental_raw_to_silver(raw_root, silver_root)
    incremental_silver_to_gold(silver_root, gold_root)
    for name, rows in expected.items():
        assert _rows(gold_root, name) == rows


def test_incremental_gold_migrates_legacy_schema_and_rebuilds_completely(tmp_path):
    raw_root = tmp_path / "raw"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    _populate_raw(raw_root)
    incremental_raw_to_silver(raw_root, silver_root)
    _write_legacy_gold(silver_root, gold_root)
    station_path = gold_root / "dim_station.parquet"
    station_table = pq.read_table(station_path)
    stale = station_table.to_pylist()[0]
    stale["station_id"] = "STALE"
    pq.write_table(
        pa.Table.from_pylist(
            station_table.to_pylist() + [stale], schema=station_table.schema
        ),
        station_path,
    )

    incremental_silver_to_gold(silver_root, gold_root)

    for name in GOLD_TABLES:
        assert pq.read_table(gold_root / f"{name}.parquet").schema == GOLD_SCHEMAS[name]
    station = _rows(gold_root, "fact_station_availability")[0]
    assert station["observed_at_local"] == station["observed_at"] + timedelta(hours=2)
    assert station["date_key"] == int(station["observed_at_local"].strftime("%Y%m%d"))
    assert station["hour_of_day"] == station["observed_at_local"].hour
    assert all(row["station_id"] != "STALE" for row in _rows(gold_root, "dim_station"))
    system = _rows(gold_root, "gold_system_availability")
    assert all(
        row["available_stations"] == row["station_count"] - row["empty_station_count"]
        for row in system
    )


def test_incremental_gold_failure_preserves_previous_output(tmp_path, monkeypatch):
    raw_root = tmp_path / "raw"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    _populate_raw(raw_root)
    incremental_raw_to_silver(raw_root, silver_root)
    incremental_silver_to_gold(silver_root, gold_root)
    before = {
        name: (gold_root / f"{name}.parquet").read_bytes() for name in GOLD_TABLES
    }

    def fail_transform(*args, **kwargs):
        raise RuntimeError("simulated Gold transform failure")

    monkeypatch.setattr(incremental_module, "transform_silver_to_gold", fail_transform)
    with pytest.raises(RuntimeError, match="simulated Gold transform failure"):
        incremental_silver_to_gold(silver_root, gold_root)
    assert {
        name: (gold_root / f"{name}.parquet").read_bytes() for name in GOLD_TABLES
    } == before


def test_incremental_gold_schema_failure_preserves_previous_output(
    tmp_path, monkeypatch
):
    raw_root = tmp_path / "raw"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    _populate_raw(raw_root)
    incremental_raw_to_silver(raw_root, silver_root)
    incremental_silver_to_gold(silver_root, gold_root)
    before = {
        name: (gold_root / f"{name}.parquet").read_bytes() for name in GOLD_TABLES
    }
    original = incremental_module.transform_silver_to_gold

    def invalid_transform(silver, candidate_root):
        candidate = original(silver, candidate_root)
        path = candidate["dim_station"]
        table = pq.read_table(path)
        fields = [
            field
            for field in GOLD_SCHEMAS["dim_station"]
            if field.name != "observed_at_local"
        ]
        rows = [
            {key: value for key, value in row.items() if key != "observed_at_local"}
            for row in table.to_pylist()
        ]
        pq.write_table(pa.Table.from_pylist(rows, schema=pa.schema(fields)), path)
        return candidate

    monkeypatch.setattr(
        incremental_module, "transform_silver_to_gold", invalid_transform
    )
    with pytest.raises(ValueError, match="Gold candidate schema mismatch"):
        incremental_silver_to_gold(silver_root, gold_root)
    assert {
        name: (gold_root / f"{name}.parquet").read_bytes() for name in GOLD_TABLES
    } == before


def test_incremental_failure_leaves_previous_state_restartable(tmp_path):
    raw_root = tmp_path / "raw"
    silver_root = tmp_path / "silver"
    _populate_raw(raw_root)
    transform_raw_to_silver(raw_root, silver_root)
    before = _rows(silver_root, "station_status")

    _append_snapshot(raw_root, 2)
    with pytest.raises(RuntimeError, match="simulated"):
        incremental_raw_to_silver(
            raw_root,
            silver_root,
            on_snapshot=lambda path: (_ for _ in ()).throw(
                RuntimeError("simulated failure")
            ),
        )
    assert _rows(silver_root, "station_status") == before

    incremental_raw_to_silver(raw_root, silver_root)
    assert len(_rows(silver_root, "station_status")) == 3


def test_incremental_rejects_conflicting_duplicate_identity(tmp_path):
    raw_root = tmp_path / "raw"
    silver_root = tmp_path / "silver"
    _append_snapshot(raw_root, 1)
    duplicate = raw_root / "station_status" / "duplicate" / "snapshot.parquet"
    duplicate.parent.mkdir(parents=True)
    source = next((raw_root / "station_status").glob("**/snapshot.parquet"))
    table = pq.read_table(source)
    table = table.set_column(
        table.schema.get_field_index("data_json"),
        "data_json",
        pa.array(['{"stations": [{"station_id": "S1"}]}']),
    )
    pq.write_table(table, duplicate)
    with pytest.raises(ValueError, match="conflicting raw snapshot identity"):
        incremental_raw_to_silver(raw_root, silver_root)
