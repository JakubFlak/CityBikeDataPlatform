# Architecture Decisions

## ADR-001 — Raw data stored as Parquet

Status: Accepted

### Context

The project collects high-frequency GBFS snapshots.

The raw layer should be efficient for append-heavy storage and analytical processing while remaining simple to operate locally.

### Decision

Raw snapshots will initially be stored as Parquet files.

### Reasoning

- columnar format
- compression
- efficient analytical reads
- works naturally with DuckDB
- suitable for partitioned historical data
- keeps raw storage independent from the analytical database

### Alternatives

- PostgreSQL
- JSON
- CSV

---

## ADR-002 — Start with local infrastructure

Status: Accepted

### Context

The project is primarily a portfolio and learning project.

There is no current requirement for cloud-scale infrastructure.

### Decision

The first version will run locally.

### Reasoning

- lower operational complexity
- lower cost
- faster development
- easier debugging
- sufficient for the expected initial data volume

Infrastructure should become more complex only when there is a concrete requirement.

### Alternatives

- cloud-first architecture
- managed data warehouse
- VPS from the beginning

---

## ADR-003 — Use Python for ingestion

Status: Accepted

### Context

GBFS is exposed through HTTP/JSON feeds and requires periodic collection.

### Decision

Python will be used for the ingestion layer.

### Reasoning

- strong HTTP/JSON ecosystem
- good testing support
- suitable for scheduled data collection
- integrates naturally with the rest of the project
- provides useful engineering experience

---

## ADR-004 — Use one-minute initial polling for GBFS

Status: Accepted

### Context

GBFS feeds are updated approximately every 60 seconds.

Short bike trips may not be visible if snapshots are collected too infrequently.

### Decision

The initial continuous collector will target approximately one-minute polling.

### Reasoning

This maximises temporal resolution during the initial data-collection experiment.

The actual data volume and usefulness of the additional resolution should be measured.

### Important

One-minute polling does not guarantee complete trip reconstruction.

GBFS is snapshot-based rather than event-based.

### Alternatives

- 5-minute polling
- 10-minute polling
- 15-minute polling

The polling interval may be changed later based on observed data volume and analytical requirements.

---

## ADR-005 — DuckDB as initial analytical database

Status: Accepted

### Context

The project requires an analytical SQL engine for local development.

### Decision

DuckDB will be used for the initial analytical layer.

### Reasoning

- excellent analytical performance
- native Parquet support
- simple local operation
- SQL interface
- easy integration with Python
- appropriate for the project's initial scale

---

## ADR-006 — dbt for analytical transformations

Status: Accepted

### Context

The project should demonstrate a modern analytics engineering workflow with explicit transformations, testing and documentation.

### Decision

dbt will be used for analytical transformations on top of DuckDB.

### Reasoning

- SQL-based transformations
- dependency management between models
- data quality tests
- documentation
- clear separation between ingestion and transformation

---

## ADR-007 — Do not treat GBFS snapshots as authoritative trip data

Status: Accepted

### Context

GBFS provides snapshots of current system state, not completed rental events.

### Decision

Trips will not be considered authoritative when inferred solely from GBFS snapshots.

### Reasoning

A bike can disappear from one snapshot and later appear elsewhere without providing complete information about:

- exact trip start
- exact trip end
- actual rental event
- intermediate locations
- whether the bike was temporarily unavailable for another reason

Authoritative trip data should come from the Wrocław Open Data historical trip source when available.

### Consequence

If trip reconstruction is implemented later, inferred trips must be clearly separated from authoritative trips.

---

## ADR-008 — Keep raw data separate from analytical models

Status: Accepted

### Context

The project needs reproducibility and the ability to reprocess historical data.

### Decision

Raw source data and transformed analytical data will be stored separately.

### Reasoning

This allows:

- reprocessing
- debugging
- testing transformation logic
- changing analytical models without recollecting source data
- preserving source history