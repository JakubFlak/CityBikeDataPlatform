"""Quality checks for the raw GBFS Parquet layer."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

REQUIRED_COLUMNS = (
    "feed_name",
    "source_url",
    "observed_at",
    "last_updated",
    "ttl",
    "version",
    "data_json",
    "source_payload_json",
)

FEED_EXPECTATIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "vehicle_types": ("vehicle_types", ("vehicle_type_id",)),
    "station_information": ("stations", ("station_id", "lat", "lon", "name")),
    "station_status": ("stations", ("station_id",)),
    "free_bike_status": ("bikes", ("bike_id",)),
    "system_pricing_plans": ("plans", ("plan_id",)),
    "system_regions": ("regions", ("region_id",)),
}


@dataclass(frozen=True)
class QualityIssue:
    """A quality finding with an explicit severity."""

    severity: str
    check: str
    message: str


@dataclass
class RawFileReport:
    """Inspection result for one raw Parquet file."""

    path: Path
    row_count: int = 0
    schema: dict[str, str] = field(default_factory=dict)
    feed_names: set[str] = field(default_factory=set)
    issues: list[QualityIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[QualityIssue]:
        """Return fatal data-quality findings."""

        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[QualityIssue]:
        """Return informational findings that do not invalidate the file."""

        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        """Whether the file has no fatal quality findings."""

        return not self.errors


def inspect_raw_file(path: Path) -> RawFileReport:
    """Inspect one raw Parquet file without modifying it."""

    table = pq.read_table(path)
    report = RawFileReport(
        path=path,
        row_count=table.num_rows,
        schema={field.name: str(field.type) for field in table.schema},
    )
    _check_required_columns(report)
    if report.errors:
        return report

    rows = table.to_pylist()
    if table.num_rows != 1:
        _error(
            report,
            "snapshot_grain",
            f"expected exactly one snapshot row, found {table.num_rows}",
        )

    for row_number, row in enumerate(rows):
        _inspect_row(report, row, row_number)
    return report


def inspect_raw_directory(root: Path) -> list[RawFileReport]:
    """Inspect all Parquet snapshots below a raw-data directory."""

    return [inspect_raw_file(path) for path in sorted(root.glob("**/*.parquet"))]


def _check_required_columns(report: RawFileReport) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in report.schema]
    if missing:
        _error(report, "required_columns", f"missing columns: {', '.join(missing)}")


def _inspect_row(report: RawFileReport, row: dict[str, Any], row_number: int) -> None:
    prefix = f"row {row_number}: "
    for column in REQUIRED_COLUMNS:
        if row.get(column) is None or row.get(column) == "":
            _error(report, "metadata_not_null", f"{prefix}{column} is null or empty")

    observed_at = row.get("observed_at")
    if isinstance(observed_at, str):
        try:
            parsed_observed_at = datetime.fromisoformat(observed_at)
            if (
                parsed_observed_at.tzinfo is None
                or parsed_observed_at.utcoffset() is None
            ):
                _error(
                    report, "observed_at", f"{prefix}timestamp is not timezone-aware"
                )
        except ValueError:
            _error(report, "observed_at", f"{prefix}invalid ISO-8601 timestamp")
    else:
        _error(report, "observed_at", f"{prefix}timestamp must be a string")

    last_updated = row.get("last_updated")
    if isinstance(last_updated, bool) or not isinstance(last_updated, int):
        _error(report, "last_updated", f"{prefix}must be a Unix timestamp integer")
    else:
        try:
            datetime.fromtimestamp(last_updated, UTC)
        except (OverflowError, OSError, ValueError):
            _error(report, "last_updated", f"{prefix}is outside timestamp range")

    ttl = row.get("ttl")
    if isinstance(ttl, bool) or not isinstance(ttl, int) or ttl < 0:
        _error(report, "ttl", f"{prefix}must be a non-negative integer")

    data = _parse_json(report, row.get("data_json"), "data_json", prefix)
    source_payload = _parse_json(
        report, row.get("source_payload_json"), "source_payload_json", prefix
    )
    if not isinstance(data, dict) or not isinstance(source_payload, dict):
        return

    source_data = source_payload.get("data")
    if source_data != data:
        _error(
            report,
            "payload_equivalence",
            f"{prefix}source data does not match data_json",
        )

    for metadata in ("last_updated", "ttl", "version"):
        if metadata in source_payload and source_payload[metadata] != row.get(metadata):
            _error(
                report,
                "metadata_consistency",
                f"{prefix}{metadata} differs from source_payload_json",
            )

    feed_name = row.get("feed_name")
    if not isinstance(feed_name, str):
        _error(report, "feed_name", f"{prefix}must be a string")
        return
    report.feed_names.add(feed_name)
    expectation = FEED_EXPECTATIONS.get(feed_name)
    if expectation is None:
        _error(report, "feed_name", f"{prefix}unknown required feed: {feed_name}")
        return

    collection_name, required_fields = expectation
    collection = data.get(collection_name)
    if not isinstance(collection, list):
        _error(
            report,
            "collection_type",
            f"{prefix}data.{collection_name} must be an array",
        )
        return
    if not collection:
        _error(
            report, "collection_not_empty", f"{prefix}data.{collection_name} is empty"
        )
    for index, item in enumerate(collection):
        if not isinstance(item, dict):
            _error(
                report,
                "item_structure",
                f"{prefix}data.{collection_name}[{index}] must be an object",
            )
            continue
        for field_name in required_fields:
            if item.get(field_name) is None or item.get(field_name) == "":
                _error(
                    report,
                    "required_item_field",
                    f"{prefix}data.{collection_name}[{index}] missing {field_name}",
                )


def _parse_json(
    report: RawFileReport, value: Any, column: str, prefix: str
) -> Any | None:
    if not isinstance(value, str):
        _error(report, "json_validity", f"{prefix}{column} must be a JSON string")
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        _error(report, "json_validity", f"{prefix}{column} is invalid JSON")
        return None


def _error(report: RawFileReport, check: str, message: str) -> None:
    report.issues.append(QualityIssue("error", check, message))
