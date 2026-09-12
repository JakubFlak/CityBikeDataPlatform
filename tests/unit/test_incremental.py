from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from test_gold import _populate_raw, _write_raw_snapshot

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

    expected = {
        name: _rows(gold_root, name)
        for name in ("fact_station_availability", "gold_system_availability")
    }
    incremental_raw_to_silver(raw_root, silver_root)
    incremental_silver_to_gold(silver_root, gold_root)
    for name, rows in expected.items():
        assert _rows(gold_root, name) == rows


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
