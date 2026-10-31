# Incremental Processing

The local pipeline is implemented as Python library functions and scripts.
There is no database, cloud state store, or orchestration framework.

## Snapshot identity and state

A Raw observation is identified by:

```text
feed_name + "|" + observed_at
```

`observed_at` is an application-generated UTC timestamp and is also encoded
in the Raw directory path. The Raw `data_json` payload is SHA-256 hashed in
`data/silver/_incremental_state.json`. Replaying the same identity and hash
is idempotent; a different payload under the same identity fails explicitly.
The source URL is retained for lineage and is not part of the identity.

The manifest is a processed-snapshot registry, not a time-only watermark.
It allows feeds to have independent collection times and does not depend on
strictly ordered arrivals. A Raw snapshot is pending if the identity is
absent or its manifest status is incomplete.

## Raw-to-Silver

The incremental transform reads metadata for Raw files and parses only
pending snapshots. It merges existing Silver rows using table-specific
natural keys:

- entity + `observed_at` for canonical feed tables;
- station + vehicle type + `observed_at` for vehicle availability;
- plan + tier index + `observed_at` for pricing tiers.

All Silver tables are staged and atomically replaced only after successful
materialization. The state manifest is written after the data commit. A
failure before completion leaves the snapshots eligible for retry.
Because each table currently uses a single Parquet file, output files are
rewritten on commits even though only new Raw payloads require parsing.

## Silver-to-Gold

Gold is regenerated as a complete projection from current Silver tables.
Candidate schemas and data are staged and validated before replacement. The
Gold stage does not merge with previous Gold outputs. This rebuild makes
schema changes deterministic and avoids stale historical aggregates.

Temporal matching uses the nearest feed observation within five minutes;
missing, ambiguous, or out-of-tolerance matches fail. `observed_at_local` is
presentation and calendar data only. UTC `observed_at` remains the snapshot
identity and matching basis.

## Normal entrypoint and transformation-only command

Run the complete coordinator with:

```powershell
uv run python scripts/run_pipeline.py
```

This performs ingestion and Raw quality checks before incremental
transformations, then marks snapshots complete only after Gold succeeds.
To transform already-collected Raw files without performing ingestion or the
coordinator's Raw quality stage, use:

```powershell
uv run python scripts/transform_incremental.py
```

The command is safe to rerun: previously processed snapshots do not append
duplicate Silver rows, and Gold is rebuilt from current Silver.

## Guarantees and limitations

- Identical snapshot replay is idempotent; conflicting same-identity data
  fails explicitly.
- Silver writes are staged, and state is persisted after successful data
  materialization.
- Gold is a full deterministic projection and is replaced only after a
  candidate build succeeds.
- This is local single-file Parquet processing; incremental commits rewrite
  output files.
- The manifest and datasets are local state and must be backed up together
  for recovery across machines.
- There is no built-in long-term retention policy or cloud backup.

See [the architecture](ARCHITECTURE.md) and
[orchestration details](ORCHESTRATION.md).
