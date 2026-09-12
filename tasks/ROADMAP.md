# Project Roadmap

The roadmap describes the major stages of the project.

Only the current phase should be implemented. Future phases are intentionally not part of the current development scope.

---

## Phase 1 — Foundation

- [x] Project structure
- [x] Python environment and packaging
- [x] Configuration
- [x] Logging
- [x] Testing foundation
- [x] Development tooling

---

## Phase 2 — GBFS Ingestion

- [x] GBFS client
- [x] GBFS feed discovery
- [x] `station_information` ingestion
- [x] `station_status` ingestion
- [x] `free_bike_status` ingestion
- [x] `vehicle_types` ingestion
- [x] `system_pricing_plans` ingestion
- [x] `system_regions` ingestion
- [x] Raw Parquet storage
- [x] Schema validation
- [x] Ingestion tests
- [x] Error handling
- [x] Silver/staging table definitions
- [x] Raw-to-Silver transformation
- [x] Silver transformation tests

---

## Phase 3 — Orchestration

- [ ] Docker
- [ ] Airflow
- [ ] Ingestion DAG
- [x] Scheduling
- [x] Retries
- [x] Failure handling
- [x] Basic monitoring

---

## Phase 4 — Analytics Engineering

- [ ] DuckDB
- [ ] dbt
- [ ] Staging models
- [x] Dimensions
- [x] Fact models
- [ ] Incremental processing
- [ ] dbt tests
- [x] Analytical aggregations
- [x] Incremental local processing

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