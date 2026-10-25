# Architecture

## Current implementation

The platform collects Wrocław Nextbike GBFS snapshots, preserves them as Raw
Parquet, incrementally builds typed Silver Parquet tables, and generates Gold
analytical Parquet tables for Power BI.

```text
Nextbike GBFS
    -> Python ingestion
    -> Raw Parquet + quality checks
    -> incremental Raw-to-Silver
    -> Silver Parquet
    -> complete Silver-to-Gold projection
    -> Gold Parquet
    -> Power BI PBIP report
```

Python implements ingestion and transformations. DuckDB, dbt, Docker, and
Airflow are not part of the current runtime. The pipeline uses local files and
is intentionally kept simple. See [incremental processing](INCREMENTAL_PROCESSING.md)
and [orchestration](ORCHESTRATION.md) for operational details.

## Data layers

### Raw

Raw preserves provider payloads and application `observed_at` timestamps as
one Parquet snapshot per GBFS feed observation. It is append-oriented and
supports reprocessing and audit. Generated Raw data is excluded from Git.

### Silver

Silver converts the six canonical GBFS feeds into typed tables and normalizes
station vehicle-type availability and pricing tiers into child tables. The
incremental manifest identifies completed snapshots; replay is idempotent and
conflicting replays fail explicitly.

### Gold

Gold is rebuilt as a deterministic analytical projection from the current
Silver state. It contains snapshot-grained dimensions and facts plus the
system-level availability aggregate. `observed_at` is canonical UTC identity;
`observed_at_local` is the `Europe/Warsaw` presentation timestamp. A snapshot
is an observed state, not a trip or utilization event. See [Gold model](GOLD_MODEL.md).

### Power BI

The PBIP project is in `dashboard/`. It contains System Overview, Station
Analysis, and Bikes Analysis pages and consumes Gold Parquet directly. Power
Query currently references local absolute Gold paths; the local report requires
the expected files and path on the developer machine. See [Power BI model](POWER_BI_MODEL.md)
for opening and refreshing it.

## Execution and retention

`python scripts/run_pipeline.py` runs the one-shot pipeline locally. GitHub
Actions runs it hourly at minute 17 and supports manual dispatch. Successful
workflow artifacts preserve pipeline state for subsequent scheduled runs, but
they expire after 14 days and are not durable historical storage. See
[orchestration](ORCHESTRATION.md).

## Future evolution

The future cloud migration is not implemented. When long-term retention,
reliable refresh, or operational requirements justify it, evaluate durable
object storage, backup/retention, alerting, and a Power BI-accessible refresh
path. Preserve Raw/Silver/Gold boundaries and snapshot semantics during that
migration; do not introduce infrastructure only to match a technology list.