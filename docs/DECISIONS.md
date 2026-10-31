# Architecture Decisions

This file preserves the project's decision history while distinguishing
implemented choices from proposals that were never adopted.

## ADR-001 — Preserve Raw snapshots in Parquet

**Status: Accepted and implemented.**

Raw observations are stored as Parquet snapshots to preserve source payloads
and support deterministic local reprocessing without requiring a database.
Parquet is a file format here; it does not imply DuckDB is used.

## ADR-002 — Start with local infrastructure

**Status: Accepted and implemented for v1.0.**

The pipeline uses local Python and Parquet because the portfolio project does
not require cloud-scale infrastructure. Local data/state durability, machine
availability, and Power BI path portability remain limitations.

## ADR-003 — Use Python for GBFS ingestion and transformations

**Status: Accepted and implemented.**

Python handles feed discovery, HTTP retrieval, envelope validation, snapshot
storage, quality checks, and Raw/Silver/Gold transformations. `uv` manages
dependencies; `pytest` and Ruff provide validation.

## ADR-004 — Approximately one-minute GBFS polling

**Status: Proposed; not the implemented schedule.**

One-minute polling was considered because feeds can refresh frequently, but
the checked-in Windows Task Scheduler export is configured for hourly runs.
The actual task registration and current collection cadence depend on the
local Windows machine. GBFS polling cadence does not guarantee trip
reconstruction.

## ADR-005 — DuckDB as initial analytical database

**Status: Not implemented; superseded by local Parquet transformations.**

The current code reads and writes Parquet through Python/PyArrow and does not
use DuckDB. Retaining this historical proposal does not make DuckDB a
dependency or a current architecture decision.

## ADR-006 — dbt for analytical transformations

**Status: Not implemented; superseded by Python transformations.**

The current project does not use dbt. Typed Silver and deterministic Gold
transformations are implemented in Python. A future SQL transformation tool
would require an explicit need and a documented design decision.

## ADR-007 — Do not treat GBFS snapshots as authoritative trips

**Status: Accepted and implemented as a scope rule.**

Snapshots cannot establish exact trip starts, ends, routes, or completed
rentals. Authoritative trip reporting requires a trustworthy trip source.
Any future inferred trip dataset must remain explicitly separate from
authoritative source facts.

## ADR-008 — Keep source and analytical data separate

**Status: Accepted and implemented.**

Raw preserves source snapshots, Silver contains typed source records, and
Gold contains analytical tables. This separation supports auditability and
reprocessing without overwriting the original provider payload.

## Future decisions

No Azure/Fabric service or cloud runtime has been selected. v2.0 must evaluate
storage, compute/orchestration, identity and secrets, monitoring, costs,
Power BI refresh, and deployment automation against concrete requirements.
GitHub remains a potential code, documentation, review, and CI/CD platform
even if runtime and datasets move to cloud services. See
[the roadmap](../tasks/ROADMAP.md).
