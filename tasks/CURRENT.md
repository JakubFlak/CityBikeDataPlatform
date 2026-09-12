# Current Task

## Task

Analytical/Gold Model

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
- Add temporal snapshot dimensions, station availability facts, free-bike
    snapshots, and reusable system/station metrics.
- Add deterministic multi-snapshot Gold transformation tests and documentation.

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
- Station availability is the central fact at `station_id + observed_at`.
- Vehicle-type availability remains a separate child fact to avoid repeating
    station-level measures.
- Free-bike snapshots remain state observations and are not interpreted as
    trips or utilization.

## Next Task

Evaluate orchestration and incremental processing only when the next phase
requires them; do not introduce them as part of the Gold model.

