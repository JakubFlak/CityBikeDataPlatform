# CityBikeDataPlatform

A local data platform and Power BI portfolio project using Wrocław Nextbike
GBFS snapshots. The Python pipeline preserves source snapshots in Raw,
incrementally builds typed Silver Parquet tables, and generates analytical
Gold Parquet tables for Power BI. These are observed states, not authoritative
trips or utilization.

## Run locally

Install dependencies and run the one-shot pipeline from the repository root:

```text
uv sync
uv run python scripts/run_pipeline.py
```

The command performs ingestion, Raw quality validation, incremental
Raw-to-Silver processing, and Silver-to-Gold transformation. Run it manually
whenever needed. GitHub Actions schedules the same pipeline hourly at minute
17 and supports manual dispatch; there is no local always-on scheduler. See
[orchestration](docs/ORCHESTRATION.md) and
[incremental processing](docs/INCREMENTAL_PROCESSING.md) for details.
Generated data under `data/` is runtime state and is not tracked in Git.

## Power BI

Open [`dashboard/Dashboard.pbip`](dashboard/Dashboard.pbip) in Power BI Desktop.
The report contains System Overview, Station Analysis, and Bikes Analysis.
Refresh requires locally generated Gold Parquet files. The current model uses
machine-local absolute paths to `data/gold`; refresh on another machine
requires local path configuration. See
[Power BI model and local refresh](docs/POWER_BI_MODEL.md) and
[analytics conventions](docs/POWER_BI_ANALYTICS.md).

## Architecture and future work

The implemented pipeline uses Python and Parquet; DuckDB and dbt are not part
of the current runtime. See [current architecture](docs/ARCHITECTURE.md). A
future cloud migration may replace local storage and temporary workflow
artifacts with durable managed storage when there is a concrete requirement.

## Development checks

```text
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
