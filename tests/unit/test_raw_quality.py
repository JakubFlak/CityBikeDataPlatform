import json
from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq

from bike_data.raw_quality import inspect_raw_file


def write_snapshot(tmp_path, payload, *, feed_name="station_status", **overrides):
    row = {
        "feed_name": feed_name,
        "source_url": "https://example.test/feed.json",
        "observed_at": datetime(2026, 9, 12, tzinfo=UTC).isoformat(),
        "last_updated": 1789163968,
        "ttl": 60,
        "version": "2.3",
        "data_json": json.dumps(payload["data"]),
        "source_payload_json": json.dumps(payload),
        **overrides,
    }
    path = tmp_path / "snapshot.parquet"
    pq.write_table(pa.table({key: [value] for key, value in row.items()}), path)
    return path


def valid_payload():
    return {
        "last_updated": 1789163968,
        "ttl": 60,
        "version": "2.3",
        "data": {"stations": [{"station_id": "1"}]},
    }


def test_valid_raw_snapshot_passes_checks(tmp_path):
    report = inspect_raw_file(write_snapshot(tmp_path, valid_payload()))

    assert report.is_valid
    assert report.row_count == 1
    assert report.errors == []


def test_invalid_json_and_metadata_are_fatal(tmp_path):
    report = inspect_raw_file(
        write_snapshot(
            tmp_path,
            valid_payload(),
            data_json="not-json",
            source_payload_json="not-json",
            observed_at="2026-09-12T00:00:00",
            ttl=-1,
        )
    )

    checks = {issue.check for issue in report.errors}
    assert {"json_validity", "observed_at", "ttl"} <= checks


def test_payload_metadata_and_collection_shape_are_checked(tmp_path):
    payload = valid_payload()
    payload["last_updated"] += 1
    payload["data"]["stations"] = {"station_id": "1"}
    report = inspect_raw_file(
        write_snapshot(
            tmp_path,
            payload,
            last_updated=1789163968,
            data_json=json.dumps({"stations": {"station_id": "2"}}),
        )
    )

    checks = {issue.check for issue in report.errors}
    assert {"payload_equivalence", "metadata_consistency", "collection_type"} <= checks


def test_feed_specific_fields_and_empty_collections_are_checked(tmp_path):
    payload = valid_payload()
    payload["data"]["stations"] = [{"station_id": ""}]
    report = inspect_raw_file(write_snapshot(tmp_path, payload))

    assert any(issue.check == "required_item_field" for issue in report.errors)


def test_multiple_rows_fail_snapshot_grain(tmp_path):
    path = write_snapshot(tmp_path, valid_payload())
    table = pq.read_table(path)
    pq.write_table(pa.concat_tables([table, table]), path)

    report = inspect_raw_file(path)

    assert any(issue.check == "snapshot_grain" for issue in report.errors)
