# Architecture

## Project Goal

The project is a data platform for collecting and analysing Wrocław Bike Sharing data.

The primary goal is to build a realistic end-to-end data engineering and analytics workflow using real operational data from the Wrocław bike-sharing system.

The project starts as a local platform. It should remain simple until there is a clear reason to introduce additional infrastructure.

## Current V1 Architecture

```text
                 Nextbike GBFS
                      │
                      ▼
               Python ingestion
                      │
                      ▼
                Raw Parquet
                      │
                      ▼
                   DuckDB
                      │
                      ▼
                    dbt
                      │
                      ▼
                 Power BI
```

This represents the planned V1 architecture.

Individual components should only be considered implemented when they actually exist in the repository.

## Data Flow

### 1. Source

The primary live source is the Nextbike GBFS API.

The API provides:

- station metadata
- current station availability
- current bike availability
- vehicle type metadata
- pricing information

The API provides snapshots of the current system state. It is not a trip-event API.

### 2. Ingestion

Python is responsible for retrieving GBFS data and converting API responses into structured records.

The ingestion layer should:

- retrieve data from the API
- validate HTTP/API responses
- preserve source information
- attach an observation timestamp
- write raw data without applying analytical transformations

The ingestion layer should not contain business logic that belongs to the transformation layer.

### 3. Raw Storage

Raw GBFS snapshots are initially stored as Parquet files.

Raw data should remain as close as reasonably possible to the source data.

The raw layer is intended to provide:

- reproducibility
- historical snapshots
- debugging capability
- the ability to reprocess data later

Raw data should not be committed to Git.

### 4. Analytical Storage

DuckDB is used as the initial analytical database.

DuckDB reads the raw Parquet data and provides the analytical layer used by dbt.

### 5. Transformation

dbt is responsible for transforming raw data into analytical models.

The transformation layer should contain:

- staging models
- dimensions
- fact tables
- data quality tests
- analytical aggregations where justified

Business logic should primarily live in this layer rather than in the ingestion code.

### 6. BI

Power BI is the presentation layer.

It should consume curated analytical models rather than raw API snapshots.

The Power BI model should focus on:

- operational availability
- station utilisation
- bike availability
- temporal patterns
- trip analysis when authoritative trip data becomes available

## Important Architectural Principles

### Separate ingestion from transformation

Python ingestion retrieves and stores source data.

dbt transformations turn stored data into analytical models.

Do not mix these responsibilities without a clear reason.

### Preserve raw data

Raw source data should be retained before analytical transformations are applied.

### Define table grain explicitly

Every analytical table must have a clearly defined grain.

### Do not invent data

The system must distinguish between:

- authoritative source data
- observed snapshot data
- derived analytical metrics
- inferred events

Inferred trips must never be presented as authoritative trips.

### Prefer simple solutions

Technology should be introduced because the project needs it, not simply to demonstrate that the technology was used.

The initial platform is intentionally local.

Future infrastructure should be introduced only when the project's requirements justify it.