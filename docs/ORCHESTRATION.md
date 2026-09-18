# Lightweight Orchestration

The project runs one complete pipeline job and exits. Scheduling is provided
by the caller, not by a long-running Python process.

## Execution graph

```text
GBFS discovery and ingestion
    -> Raw Parquet snapshots
    -> Raw quality validation
    -> incremental Raw -> Silver
    -> incremental Silver -> Gold
    -> Gold schema validation
    -> Parquet output row-count validation and run summary
```

`python scripts/run_pipeline.py` is the local one-command entrypoint. It
constructs the existing GBFS ingestor, validates every Raw file, then calls
the existing incremental transformation functions. It does not duplicate
transformation logic.

Ingestion, quality validation, Silver, and Gold are critical stages. Any
exception stops the run and the command exits with status 1. Silver remains an
incremental, key-deduplicated layer; Gold is rebuilt as a complete projection
of the current Silver state. Both outputs use staged writes and validation
before replacement. The Raw-to-Silver manifest is written only after Silver
commits, with a `silver_complete` status. The coordinator changes that status
to `complete` only after Gold commits, so a failed Silver or Gold run retries
its snapshots on the next run.

## Scheduling and manual runs

`.github/workflows/data-pipeline.yml` runs hourly at minute 17 (`17 * * * *`).
This is conservative for a portfolio polling job and avoids unnecessary API
load while remaining more frequent than a daily refresh. The workflow also
supports `workflow_dispatch` for a manual run from the GitHub Actions UI.

The CI workflow is separate in `.github/workflows/ci.yml`; it runs tests and
Ruff but never calls the public GBFS service.

## GitHub Actions persistence

GitHub-hosted runners are ephemeral. Before running the pipeline,
`data-pipeline.yml` queries successful runs of the same workflow with the
GitHub CLI, selects the most recent successful run, and downloads its
`pipeline-state` artifact into the workspace. The workflow grants `actions: read`
for this lookup. The restore helper also accepts the previous
`pipeline-output-<run_id>` naming for the first deployment of this fix.

If no successful run exists, the download step is skipped and the job starts
with an empty `data/` directory. Once a run succeeds, the complete `data/`
directory, including Raw, Silver, Gold, and
`data/silver/_incremental_state.json`, is uploaded as the new `pipeline-state`
artifact. The next run restores it before ingestion, so completed snapshot
identities remain recognized and new snapshots are appended.

The successful-state upload runs only when the pipeline succeeds. A failed run
can upload a separate `pipeline-failure-<run_id>` diagnostic artifact, but it
cannot replace `pipeline-state`; downstream failures therefore leave the last
known-good state available for the next run.

The workflow runs the repository version of the pipeline on every scheduled or
manual job. Before publishing `pipeline-state`, it validates every Gold table
against the current `GOLD_SCHEMAS`, including `observed_at_local` on snapshot
tables. This prevents an old restored artifact from being republished with a
stale Gold schema after a model change.

## Configuration

Settings are loaded from environment variables with local defaults:

- `BIKE_DATA_ENV`
- `BIKE_DATA_LOG_LEVEL`
- `BIKE_DATA_RAW_DIR`
- `BIKE_DATA_SILVER_DIR`
- `BIKE_DATA_GOLD_DIR`
- `BIKE_DATA_GBFS_DISCOVERY_URL`
- `BIKE_DATA_HTTP_TIMEOUT`

The current public GBFS endpoint requires no credentials or secrets.

## Artifacts and observability

Generated Raw, Silver, Gold, and the incremental manifest remain ignored by
Git. GitHub Actions artifacts are temporary portfolio-v1 persistence with a
14-day retention period, not production-grade historical storage. A future
object store can replace this without changing the pipeline stages.

Each run logs start and success/failure events, discovered/new/skipped Raw
snapshot counts, and row counts for every Silver and Gold output table.

## Limitations

- GitHub Actions artifacts are temporary operational outputs, not durable
  historical storage.
- The workflow has no external alerting or dashboard.
- Local Parquet tables are rewritten during incremental commits.
- The hourly schedule is not a substitute for a dedicated collection service
  when long-term retention or higher polling frequency is required.