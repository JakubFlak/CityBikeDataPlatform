# Architecture

## Implemented local v1.0

The project is a local Python and Parquet data platform. It collects observed
Wrocław Nextbike GBFS states and generates a Power BI-ready Gold model.
Snapshots do not represent trips or utilization.

```mermaid
flowchart LR
    GBFS[Nextbike GBFS]
    Py[Python ingestion]
    Raw[Raw Parquet]
    QA[Raw quality validation]
    Silver[Incremental Silver Parquet]
    Gold[Gold Parquet projection]
    BI[Power BI PBIP]
    GBFS --> Py --> Raw --> QA --> Silver --> Gold --> BI
```

The one-shot coordinator is `scripts/run_pipeline.py`. It performs ingestion,
Raw validation, incremental Raw-to-Silver processing, complete
Silver-to-Gold transformation, output row counts, and manifest completion.
The relevant implementation is in `src/bike_data/`.

## Layer responsibilities

### Raw

Raw retains the original provider envelope and payload together with feed
identity, source URL, and application-generated UTC `observed_at`. One file
contains one row for one feed observation. Raw is append-oriented local
history and can be reprocessed. It is not committed to Git.

### Silver

Silver parses canonical `data_json` into typed, lineage-bearing tables.
Snapshot history is preserved by entity-plus-observation keys.
Station vehicle-type counts and pricing tiers are separate child tables.
`data/silver/_incremental_state.json` records processed snapshot identities.

### Gold

Gold is a deterministic analytical projection rebuilt from all current Silver
tables. It contains temporal snapshot dimensions, station availability,
station/vehicle availability, visible-bike snapshots, and one system
availability row per station-status observation time. `observed_at` is UTC
identity; `observed_at_local` is its `Europe/Warsaw` presentation value.

### Power BI

The PBIP report imports Gold Parquet and has System Overview, Station
Analysis, and Bikes Analysis pages. Its Power Query sources currently use
absolute paths specific to the developer's checkout. See
[the model guide](POWER_BI_MODEL.md) and
[KPI semantics](POWER_BI_ANALYTICS.md).

## Data flow and temporal behavior

```text
GBFS discovery and six feeds
  -> Raw snapshots and quality inspection
  -> incremental Raw-to-Silver
  -> complete Silver-to-Gold projection
  -> Power BI import
```

Each feed is retrieved sequentially, so feed `observed_at` values in a
collection cycle are not guaranteed to match exactly. Gold uses a nearest
temporal join with a five-minute tolerance where feed alignment is required;
missing, ambiguous, or out-of-tolerance matches fail explicitly. This is not
event reconstruction.

## Scheduling and reliability

The pipeline itself is one-shot. The repository has an exported Windows Task
Scheduler definition and a PowerShell wrapper that invokes it hourly and
appends output to `logs/local_pipeline.log`. The export is tied to a machine
path and account and does not prove that a task is registered on another
computer.

`.github/workflows/ci.yml` runs tests and Ruff on pushes and pull requests.
There is no active GitHub Actions data-ingestion workflow. Data, state, and
logs are local runtime outputs.

## Deliberately not implemented

The current runtime does not use DuckDB, dbt, Docker, Airflow, cloud storage,
or a managed scheduler. It does not ingest Wrocław Open Data trips or infer
rides from GBFS. These are not hidden runtime dependencies.

## My v2.0 direction

Cloud migration is not part of v1.0. For v2.0, I plan to evaluate durable
object storage and its Raw/Silver/Gold layout, compute and orchestration
based on measured scale, managed identity and secrets, monitoring and cost
controls, a Power BI refresh path, and deployment automation. I also plan to
keep GitHub for source, documentation, review, and CI/CD. See
[my roadmap](../tasks/ROADMAP.md).
