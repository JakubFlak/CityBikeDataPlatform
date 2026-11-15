"""One-shot orchestration for the local Raw, Silver, and Gold pipeline."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from bike_data.config import Settings
from bike_data.gbfs import GBFSIngestor
from bike_data.gbfs_client import GBFSHTTPClient
from bike_data.incremental import (
    incremental_raw_to_silver,
    incremental_silver_to_gold,
    mark_snapshots_complete,
)
from bike_data.raw_quality import RawFileReport, inspect_raw_directory
from bike_data.storage import RawSnapshotStore

LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Run the pipeline CLI and return a process exit status."""

    from bike_data.config import load_settings
    from bike_data.logging import configure_logging

    settings = load_settings()
    configure_logging(settings.log_level)
    try:
        run_pipeline(settings)
    except Exception:
        LOGGER.exception("pipeline_failed")
        return 1
    return 0


@dataclass(frozen=True)
class PipelineSummary:
    """Run-level counts emitted after a successful pipeline run."""

    raw_snapshots_discovered: int
    new_snapshots_processed: int
    snapshots_skipped: int
    silver_rows: dict[str, int]
    gold_rows: dict[str, int]


def run_pipeline(
    settings: Settings,
    *,
    ingest: Callable[[], list[Path]] | None = None,
    validate: Callable[[Path], list[RawFileReport]] | None = None,
    silver: Callable[[Path, Path], dict[str, Path]] | None = None,
    gold: Callable[[Path, Path], dict[str, Path]] | None = None,
) -> PipelineSummary:
    """Run ingestion, quality checks, incremental transforms, and output checks."""

    LOGGER.info("pipeline_started environment=%s", settings.environment)
    ingest = ingest or _ingest_factory(settings)
    validate = validate or inspect_raw_directory
    silver = silver or incremental_raw_to_silver
    gold = gold or incremental_silver_to_gold

    before_count = len(list(settings.raw_data_dir.glob("**/*.parquet")))
    ingest()
    reports = validate(settings.raw_data_dir)
    _raise_for_quality_errors(reports)

    after = _snapshot_identities(settings.raw_data_dir)
    known = _processed_identities(settings.silver_data_dir)
    pending = after - known
    LOGGER.info(
        "raw_validated snapshots_discovered=%d new_snapshots=%d skipped_snapshots=%d",
        len(after),
        len(pending),
        len(after & known),
    )
    if len(after) < before_count:
        raise RuntimeError("raw snapshot count decreased during ingestion")

    silver_paths = silver(settings.raw_data_dir, settings.silver_data_dir)
    silver_rows = _count_rows(silver_paths)
    LOGGER.info("silver_completed rows=%s", json.dumps(silver_rows, sort_keys=True))

    gold_paths = gold(settings.silver_data_dir, settings.gold_data_dir)
    gold_rows = _count_rows(gold_paths)
    mark_snapshots_complete(settings.silver_data_dir, after)
    LOGGER.info("gold_completed rows=%s", json.dumps(gold_rows, sort_keys=True))
    summary = PipelineSummary(
        raw_snapshots_discovered=len(after),
        new_snapshots_processed=len(pending),
        snapshots_skipped=len(after & known),
        silver_rows=silver_rows,
        gold_rows=gold_rows,
    )
    LOGGER.info(
        "pipeline_succeeded raw_snapshots=%d new_snapshots=%d skipped_snapshots=%d",
        summary.raw_snapshots_discovered,
        summary.new_snapshots_processed,
        summary.snapshots_skipped,
    )
    return summary


def _ingest_factory(settings: Settings) -> Callable[[], list[Path]]:
    def ingest() -> list[Path]:
        return GBFSIngestor(
            client=GBFSHTTPClient(timeout=settings.http_timeout),
            store=RawSnapshotStore(settings.raw_data_dir),
            discovery_url=settings.gbfs_discovery_url,
        ).ingest_all()

    return ingest


def _raise_for_quality_errors(reports: list[RawFileReport]) -> None:
    errors = [issue for report in reports for issue in report.errors]
    if errors:
        raise ValueError(
            f"raw quality validation failed with {len(errors)} error(s): "
            f"{errors[0].check}: {errors[0].message}"
        )


def _snapshot_identities(root: Path) -> set[str]:
    identities = set()
    for path in sorted(root.glob("**/*.parquet")):
        row = pq.read_table(path, columns=["feed_name", "observed_at"]).to_pylist()[0]
        identities.add(f"{row['feed_name']}|{row['observed_at']}")
    return identities


def _processed_identities(silver_root: Path) -> set[str]:
    state_path = silver_root / "_incremental_state.json"
    if not state_path.exists():
        return set()
    state: dict[str, Any] = json.loads(state_path.read_text(encoding="utf-8"))
    return {
        identity
        for identity, metadata in state.get("raw_snapshots", {}).items()
        if metadata.get("status", "complete") == "complete"
    }


def _count_rows(paths: dict[str, Path]) -> dict[str, int]:
    return {name: pq.read_metadata(path).num_rows for name, path in paths.items()}
