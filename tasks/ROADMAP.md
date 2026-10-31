# Project Roadmap

## Completed: local v1.0

The local portfolio baseline is implemented: GBFS feed discovery and Raw
snapshot collection, Raw quality checks, typed and incremental Silver,
deterministic Gold analytics, a Power BI PBIP report, local Windows scheduling
artifacts, and automated tests/CI. See the [technical README](../README.md)
and [project overview](../docs/PROJECT_OVERVIEW.md).

DuckDB, dbt, Docker, Airflow, authoritative trip ingestion, and cloud services
are not part of this implementation. The project does not infer trip records
from GBFS observations.

## v2.0: cloud evolution

I plan to evaluate a cloud evolution for v2.0. The items below describe
direction, not implemented services or a final architecture. I intend to
preserve the Raw/Silver/Gold separation and select services only when
requirements, cost, and operational ownership justify them.

1. **Set requirements and service-selection criteria**
   - I will define collection frequency, retention, recovery objectives, expected
     data volume, refresh latency, access model, and budget.
   - I will compare Azure Data Lake Storage Gen2 / Blob Storage with Microsoft Fabric
     OneLake/Lakehouse based on data-lake control, Power BI integration,
     licensing, governance, and cost.
   - I will select a database or compute engine only after the workload and
     consumption needs are established.
2. **Design cloud data layout**
   - I plan to preserve source payloads in an append-oriented Raw zone.
   - I will define partitioning, formats, schema evolution, lifecycle retention,
     backups, and access controls for Raw/Silver/Gold.
   - I will document how the local manifest and idempotent snapshot identity map to
     cloud state.
3. **Choose execution and orchestration**
   - I plan to reuse the existing Python pipeline and decide whether a
     scheduled container/job, Azure Functions, Data Factory, or Fabric
     orchestration best fits runtime duration, operational ownership, and
     cost.
   - I will define retries, idempotency, concurrency limits, replay, and failure
     recovery; keep live ingestion outside CI test jobs.
4. **Configuration, secrets, and access**
   - I plan to move environment-specific settings out of source control.
   - I will prefer managed identity and least privilege; use Key Vault only where
     secrets are required.
   - I will separate development and production data/resource access.
5. **Observability and operations**
   - I plan to add structured run status, feed freshness and quality metrics, error
     classification, actionable alerts, retention/backup controls, and
     resource budgets.
   - I will verify data recovery and document support ownership before relying on
     the pipeline operationally.
6. **Power BI integration**
   - I will choose a Gold serving format supported by the selected architecture.
   - I plan to replace machine-local `File.Contents` paths with an appropriate managed
     connection and refresh configuration.
   - I will validate semantic relationships, KPI definitions, permissions, refresh
     behavior, and licensing with the target service.
7. **CI/CD**
   - I plan to continue using GitHub for source, documentation, pull requests, and
     automated tests even if runtime and data move to cloud services.
   - I will add environment-protected deployment workflows, identity-based
     authentication, infrastructure/configuration review, and rollback
     strategy after selecting the cloud target.

## Guiding principle

I will treat cloud migration as an evaluation and staged design effort. I
will not select Azure/Fabric services from a technology checklist or describe
planned capabilities as complete until I have implemented and validated them.
