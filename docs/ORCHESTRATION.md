# Local Orchestration

The implemented Python pipeline is a one-shot job. Scheduling is external;
the pipeline does not run as a daemon.

## Execution graph

```text
GBFS discovery and ingestion
    -> Raw Parquet snapshots
    -> Raw quality validation
    -> incremental Raw -> Silver
    -> incremental Silver -> Gold projection
    -> output row counts and completion-state update
```

The repository-root entrypoint is:

```powershell
uv run python scripts/run_pipeline.py
```

Any critical-stage exception stops the run and produces a non-zero exit
status. Silver and Gold writes are staged before replacement. Snapshots are
marked complete only after successful Gold output.

## Local Windows Task Scheduler

The repository contains:

- `scripts/run_local_pipeline.ps1`, a wrapper around the local `.venv`
  Python executable;
- `scripts/CityBikeDataPlatform - Local Pipeline.xml`, an exported Windows
  task definition configured for hourly repetition.

The wrapper sets the project root as the working directory, creates `logs/`,
waits 30 seconds, invokes `scripts/run_pipeline.py`, and appends stdout/stderr
to `logs/local_pipeline.log`. It exits with the Python pipeline's status.
The XML export contains an absolute working directory and local task
principal, so it must be reviewed and customized before reuse. A checked-in
export does not tell us whether the task is currently registered, enabled, or
running on any particular host.

## CI

`.github/workflows/ci.yml` runs on pushes and pull requests. It sets up
Python 3.12 and `uv`, installs the locked development dependencies, and runs
pytest, Ruff lint, and Ruff format checks. CI does not call the live GBFS
service and does not schedule data collection.

There is no active `data-pipeline.yml` workflow or GitHub Actions data
artifact persistence in the current repository. Local generated data and the
incremental manifest remain excluded from Git.

## Configuration

`src/bike_data/config.py` reads these environment variables, with the shown
defaults:

| Variable | Default |
| --- | --- |
| `BIKE_DATA_ENV` | `development` |
| `BIKE_DATA_LOG_LEVEL` | `INFO` |
| `BIKE_DATA_RAW_DIR` | `data/raw` |
| `BIKE_DATA_SILVER_DIR` | `data/silver` |
| `BIKE_DATA_GOLD_DIR` | `data/gold` |
| `BIKE_DATA_GBFS_DISCOVERY_URL` | `https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/gbfs.json` |
| `BIKE_DATA_HTTP_TIMEOUT` | `30` seconds |

The current public endpoint requires no credentials.

## Logs and limitations

The PowerShell wrapper appends a timestamped run boundary, project path,
pipeline output, and process exit code to `logs/local_pipeline.log`. Python
logging additionally records pipeline stage and row-count events.

The local schedule depends on the Windows host, account, network, installed
`.venv`, and local paths. There is no durable remote storage, backup/retention
service, external alerting, monitoring dashboard, or managed orchestration.
The hourly configuration is a local task export, not a guarantee of
continuous collection.

See [incremental processing](INCREMENTAL_PROCESSING.md) and the
[v2.0 roadmap](../tasks/ROADMAP.md).
