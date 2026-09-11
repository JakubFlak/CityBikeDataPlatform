# Project Roadmap

The roadmap describes the major stages of the project.

Only the current phase should be implemented. Future phases are intentionally not part of the current development scope.

---

## Phase 1 — Foundation

- [ ] Project structure
- [ ] Python environment and packaging
- [ ] Configuration
- [ ] Logging
- [ ] Testing foundation
- [ ] Development tooling

---

## Phase 2 — GBFS Ingestion

- [ ] GBFS client
- [ ] GBFS feed discovery
- [ ] `station_information` ingestion
- [ ] `station_status` ingestion
- [ ] `free_bike_status` ingestion
- [ ] `vehicle_types` ingestion
- [ ] `system_pricing_plans` ingestion
- [ ] Raw Parquet storage
- [ ] Schema validation
- [ ] Ingestion tests
- [ ] Error handling

---

## Phase 3 — Orchestration

- [ ] Docker
- [ ] Airflow
- [ ] Ingestion DAG
- [ ] Scheduling
- [ ] Retries
- [ ] Failure handling
- [ ] Basic monitoring

---

## Phase 4 — Analytics Engineering

- [ ] DuckDB
- [ ] dbt
- [ ] Staging models
- [ ] Dimensions
- [ ] Fact models
- [ ] Incremental processing
- [ ] dbt tests
- [ ] Analytical aggregations

---

## Phase 5 — BI

- [ ] Power BI semantic model
- [ ] Measures/KPIs
- [ ] Station availability analysis
- [ ] Bike availability analysis
- [ ] Time-based analysis
- [ ] Trip analysis when authoritative trip data is available
- [ ] Dashboard

---

## Phase 6 — Continuous Collection

- [ ] Dedicated collection machine
- [ ] Long-term collection
- [ ] Monitoring
- [ ] Backup
- [ ] Data retention strategy
- [ ] Operational reliability

---

## Future Evolution

After the local platform is complete and has accumulated meaningful data, the architecture may be evaluated for migration to cloud infrastructure.

Potential technologies may include cloud storage, distributed processing or managed analytics platforms.

These technologies are intentionally **out of scope for the current project**.

They should only be introduced when there is a concrete architectural or scale-related reason to do so.

---

## Guiding Principle

Do not add technology simply because it appears in the roadmap.

Each technology should solve an actual problem in the project and should be introduced at the point where that problem appears.