"""Inspect all locally stored raw GBFS Parquet snapshots."""

from pathlib import Path

from bike_data.raw_quality import inspect_raw_directory


def main() -> int:
    reports = inspect_raw_directory(Path("data/raw"))
    error_count = 0
    warning_count = 0
    for report in reports:
        print(
            f"{report.path}: rows={report.row_count}, "
            f"feeds={sorted(report.feed_names)}, "
            f"errors={len(report.errors)}, warnings={len(report.warnings)}"
        )
        for issue in report.issues:
            print(f"  {issue.severity}: {issue.check}: {issue.message}")
        error_count += len(report.errors)
        warning_count += len(report.warnings)

    print(f"Total files: {len(reports)}")
    print(f"Total errors: {error_count}")
    print(f"Total warnings: {warning_count}")
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
