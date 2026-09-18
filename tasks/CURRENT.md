# Current Task

## Task

Incremental Processing

## Status

Completed.

## Completed Work

- Discover the Polish GBFS feeds dynamically from `gbfs.json`.
- Retrieve and validate the six required GBFS feed envelopes.
- Preserve provider metadata and nested raw payloads.
- Attach a separate timezone-aware UTC `observed_at` timestamp.
- Persist one raw Parquet snapshot per feed observation.
- Add deterministic tests for discovery, HTTP failures, validation, timestamps,
  and persistence.
- Add a separate live smoke command in `scripts/gbfs_live_smoke.py`.
- Inspect all current raw Parquet files and report schema, grain, metadata,
  JSON, equivalence, and collection findings.
- Add reusable raw-layer validation in `bike_data.raw_quality`.
- Add a repeatable inspection command in `scripts/inspect_raw_quality.py`.
- Define the Silver table grains, keys, typed columns, lineage, and nested-data
    decisions.
- Transform all six canonical collections into typed Silver Parquet tables.
- Normalize station vehicle-type availability and pricing tiers into child
    tables without flattening unrelated nested structures.
- Add deterministic multi-snapshot Silver transformation tests.
- Design and implement the analytical Gold model from Silver Parquet tables.
- Add `observed_at_local` to Gold using IANA `Europe/Warsaw`; derive Gold
    calendar attributes from local time while retaining UTC snapshot identity.
- Update the Power BI semantic/report definitions to use local time for
    presentation and time-series axes.
- Add temporal snapshot dimensions, station availability facts, free-bike
    snapshots, and reusable system/station metrics.
- Add deterministic multi-snapshot Gold transformation tests and documentation.
- Define Raw snapshot identity and a restartable incremental state manifest.
- Process only unseen Raw snapshots into idempotent Silver outputs.
- Add atomic complete Gold projections from Silver and derived-model rebuild
    semantics.
- Add incremental append, rerun, failure-restart, temporal, and conflict tests.
- Add a one-command lightweight pipeline coordinator with structured run
    summaries and fail-fast stage handling.
- Redesign the Gold system consumption table around observed availability
    state and deprecate redundant all-history station metrics.
- Add separate CI and scheduled/manual GitHub Actions workflows.
- Document scheduling, configuration, retry behavior, and generated artifact
    handling.

## Constraints Honoured

- No DuckDB, dbt, orchestration, or BI semantic model was added.
- No Wroclaw-specific filtering or trip inference occurs during ingestion.
- Runtime raw data remains excluded from Git.

## Current Findings

- Six files inspected, each with exactly one snapshot row.
- All files use the expected eight-column schema.
- Zero fatal errors and zero warnings.
- Canonical `data_json` matches `source_payload_json.data` in every file.
- Provider metadata agrees with the extracted Parquet metadata in every file.
- Silver output contains eight deterministic tables: six canonical tables and
    two nested child tables.
- Two timestamp fixtures preserve time-varying rows and source lineage.
- Gold uses snapshot-grained dimensions keyed by entity plus `observed_at`.
- Gold stores `observed_at_local` as the `Europe/Warsaw` representation of the
    same instant; it is never used for keys, joins, incremental identity, or
    latest-snapshot selection.
- Station availability is the central fact at `station_id + observed_at`.
- Vehicle-type availability remains a separate child fact to avoid repeating
    station-level measures.
- Free-bike snapshots remain state observations and are not interpreted as
    trips or utilization.
- Raw identity is `feed_name + observed_at`, with a payload hash to reject
    conflicting replays.
- Incremental output commits are staged and state is written last.
- The complete execution graph is ingestion -> Raw quality -> incremental
    Silver -> incremental Gold -> output row-count summary.
- The data workflow runs hourly at minute 17 and supports `workflow_dispatch`;
    CI remains separate and never calls the live GBFS service.
- Generated data is uploaded as a short-lived GitHub Actions artifact and is
    never committed to Git.
- Scheduled and manual runs restore the latest successful pipeline-state
    artifact before ingestion; failed runs cannot replace that artifact.
- The first run starts empty when no successful state artifact exists.
- `gold_system_availability` is one row per `observed_at` and excludes
    capacity-, dock-, utilization-, and demand-based metrics.
- Station history summaries are calculated from the timestamp-grain station
    fact instead of maintained as redundant Gold output.
- Gold `date_key`, calendar attributes, and `hour_of_day` describe the local
    `Europe/Warsaw` observation date and time, including midnight and CET/CEST
    transitions.

## Next Task

Evaluate durable artifact storage and alerting only when long-term collection
requires them; do not add a heavyweight orchestration framework yet.

