# Project Overview — CityBikeDataPlatform local v1.0

## The analytical problem

Public bike-sharing feeds publish snapshots of system state, not a history of
completed rentals. A single live view is not enough to compare how station
availability changes over time, where bikes are observed, or how often a
station has no bike in the collected observations.

This project collects repeated Nextbike GBFS observations for Wrocław,
preserves the provider payload, and models the observed states so a user can
inspect station and vehicle availability over time. It deliberately does not
turn a bike disappearing from the feed into a trip.

## Decisions this report can support

The report can help an analyst:

- identify stations whose observed bike counts are repeatedly low or zero;
- compare station availability patterns by selected region and period;
- see how station-bike and e-bike counts vary between collected snapshots;
- distinguish bikes reported at stations from bikes whose GBFS
  `station_id` is null;
- inspect the visible bike locations and vehicle categories represented by
  the Power BI map.

These observations can guide follow-up analysis or operational questions.
They do not prove demand, unmet demand, trips, customer behavior, or causal
service effects, and the project has no measured savings or production
deployment claims.

## The three report pages

### System Overview

Summarizes the selected/latest system state with station-bike, outside-
station-bike, station, and empty-station counts. Snapshot trends show station
availability and a station-bike composition view. Counts across several
timestamps are repeated observations, not period totals.

### Station Analysis

Compares station-level availability rates and bike counts using the selected
date/period/grain and available station/region filters. The map, time trend,
ranking, and station table can help locate observations that merit attention.
`Station Availability Rate` is the share of observed station rows with a
positive bike count, not percentage of elapsed time.

### Bikes Analysis

Shows an e-bike share, average outside-station bike observations, and
snapshot trends for regular/e-bike station counts and outside-station bikes.
The map is intentionally limited by Power Query to latitudes 51–51.23 and
vehicle IDs `183` and `71`; it is not an unfiltered map of every GBFS bike.

## KPI interpretation matters

- **Available station bikes** is the sum of `station_status` bike counts at
  stations for one snapshot when using the latest measure.
- **Free bikes** in the system KPI means `free_bike_status` records whose
  `station_id` is null, matched to a nearby station-status timestamp. It is
  not the number available at stations.
- **Empty stations** are observed station rows with `num_bikes_available = 0`.
  An absent station observation is not automatically an empty station.
- **Station availability rates** count station observations. The System
  Overview `Station Availability %` and Station Analysis
  `Station Availability Rate` use different measures and have a null-value
  caveat.
- **E-bike share** is based on station-bike observation sums, not all
  visible bikes and not usage.
- Some latest measures use local timestamps while others use UTC, and a DAX
  measure is named as regular station e-bikes although it returns the e-bike
  field. These model caveats are reported in
  [the KPI catalogue](POWER_BI_ANALYTICS.md); they were not altered in this
  documentation-only scope.

## What is implemented and tested

The repository includes GBFS discovery and validation, Raw Parquet
preservation, quality checks, typed Silver tables, incremental snapshot
processing with a restartable manifest, deterministic Gold tables, and a
three-page Power BI PBIP report. Tests cover HTTP/ingestion behavior,
configuration, logging, data quality, state management, incremental
processing, Silver/Gold schemas and transformations, and pipeline
coordination. The current suite has 56 tests; all passed locally on Python
3.14.4. CI runs pytest and Ruff on Python 3.12.

The data platform is a local portfolio implementation. The repository does
not demonstrate a measured business outcome, a live production deployment,
or authoritative trip analytics.

## Engineering competencies demonstrated

- API discovery, validation, retries, and error handling;
- preserving source data separately from typed and analytical outputs;
- explicit table grain, keys, lineage, and UTC/local timestamp semantics;
- idempotent incremental processing and staged output commits;
- data quality checks, reproducible transformations, and automated tests;
- dimensional and snapshot-fact modeling for Power BI;
- documenting KPI filters, denominators, and interpretation limitations.

## Limitations

- No authoritative Wrocław trip history is ingested; no trips, utilization,
  demand, fares, or customer measures are supported.
- Data and incremental state are local Parquet/JSON files, with no durable
  backup, retention, alerting, or managed runtime.
- The checked-in Windows Task Scheduler export is machine-specific, and its
  local registration cannot be verified from the repository.
- Power BI imports Gold through hard-coded local absolute paths and requires
  path edits on another machine.
- The free-bike map is filtered to a limited coordinate range and two vehicle
  type IDs.
- DAX has known metric-name, null-count, and local-versus-UTC latest-time
  caveats; details are documented rather than silently corrected.

## v2.0: my planned cloud evolution

For v2.0, I plan to evaluate durable cloud storage and the Raw/Silver/Gold
layout; select Azure/Fabric services based on integration, scale, operational
ownership, and cost; run and orchestrate the existing Python transformations
in a managed environment; manage secrets and identity; add monitoring,
failure handling, retention, and cost controls; reconnect Power BI to the
chosen model; and add deployment automation.

These are my plans, not implemented services or final architecture decisions.
I plan to keep using GitHub for source code, documentation, review, and CI/CD
if I migrate the runtime or data to cloud services. See
[my v2.0 roadmap](../tasks/ROADMAP.md).
