from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts import run_pipeline as pipeline_script
from test_gold import _populate_raw

from bike_data.config import Settings
from bike_data.pipeline import run_pipeline
from bike_data.raw_quality import RawFileReport


def test_gold_failure_does_not_mark_snapshots_complete(tmp_path):
    raw_root = tmp_path / "raw"
    _populate_raw(raw_root)
    settings = Settings(
        raw_data_dir=raw_root,
        silver_data_dir=tmp_path / "silver",
        gold_data_dir=tmp_path / "gold",
    )

    with pytest.raises(RuntimeError, match="gold failed"):
        run_pipeline(
            settings,
            ingest=lambda: [],
            gold=lambda _silver_root, _gold_root: (_ for _ in ()).throw(
                RuntimeError("gold failed")
            ),
        )

    state = (settings.silver_data_dir / "_incremental_state.json").read_text()
    assert '"status": "silver_complete"' in state


def _write_identity(raw_root: Path, feed_name: str, observed_at: str) -> None:
    path = raw_root / feed_name / "snapshot" / "snapshot.parquet"
    path.parent.mkdir(parents=True)
    pq.write_table(
        pa.table({"feed_name": [feed_name], "observed_at": [observed_at]}), path
    )


def test_pipeline_runs_stages_in_order_and_reports_counts(tmp_path):
    settings = Settings(
        raw_data_dir=tmp_path / "raw",
        silver_data_dir=tmp_path / "silver",
        gold_data_dir=tmp_path / "gold",
    )
    events = []

    def ingest():
        events.append("ingest")
        _write_identity(
            settings.raw_data_dir, "station_status", "2026-09-12T00:00:00+00:00"
        )
        return []

    def validate(root):
        events.append("validate")
        return [RawFileReport(path=root / "snapshot.parquet")]

    def silver(raw_root, silver_root):
        events.append("silver")
        path = silver_root / "stations.parquet"
        path.parent.mkdir(parents=True)
        pq.write_table(pa.table({"id": [1, 2]}), path)
        return {"stations": path}

    def gold(silver_root, gold_root):
        events.append("gold")
        path = gold_root / "facts.parquet"
        path.parent.mkdir(parents=True)
        pq.write_table(pa.table({"id": [1]}), path)
        return {"facts": path}

    summary = run_pipeline(
        settings, ingest=ingest, validate=validate, silver=silver, gold=gold
    )

    assert events == ["ingest", "validate", "silver", "gold"]
    assert summary.raw_snapshots_discovered == 1
    assert summary.new_snapshots_processed == 1
    assert summary.snapshots_skipped == 0
    assert summary.silver_rows == {"stations": 2}
    assert summary.gold_rows == {"facts": 1}


def test_pipeline_propagates_ingestion_failure_and_stops(tmp_path):
    events = []

    def ingest():
        events.append("ingest")
        raise RuntimeError("ingestion failed")

    with pytest.raises(RuntimeError, match="ingestion failed"):
        run_pipeline(Settings(raw_data_dir=tmp_path / "raw"), ingest=ingest)

    assert events == ["ingest"]


def test_cli_returns_nonzero_when_pipeline_fails(monkeypatch):
    def fail(settings):
        raise RuntimeError("pipeline failed")

    monkeypatch.setattr(pipeline_script, "run_pipeline", fail)

    assert pipeline_script.main() == 1


def test_pipeline_real_incremental_run_is_idempotent(tmp_path):
    raw_root = tmp_path / "raw"
    _populate_raw(raw_root)
    settings = Settings(
        raw_data_dir=raw_root,
        silver_data_dir=tmp_path / "silver",
        gold_data_dir=tmp_path / "gold",
    )

    first = run_pipeline(settings, ingest=lambda: [])
    second = run_pipeline(settings, ingest=lambda: [])

    assert first.new_snapshots_processed == 12
    assert second.new_snapshots_processed == 0
    assert second.snapshots_skipped == 12
    assert first.silver_rows == second.silver_rows
    assert first.gold_rows == second.gold_rows
