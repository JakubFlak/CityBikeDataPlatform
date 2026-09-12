# Power BI Analytics Design

## Status

This is a design-only proposal for a future Power BI report. It does not
create a `.pbix`, generate data, add DAX to the repository, or introduce
DuckDB, dbt, or another infrastructure component.

The report must describe observed bike-sharing state honestly. GBFS provides
periodic snapshots of what was visible at collection time; it does not provide
authoritative rides, customers, revenue, or demand events.

## 1. Analytical questions

### Directly observed metrics

These are fields or aggregates directly represented by the current Gold data:

- How many bikes and docks were available at each station snapshot?
- What was the observed capacity of each station?
- How many stations were represented in a system snapshot?
- How many e-bikes were reported as available by station and timestamp?
- Which vehicle types were available at a station snapshot?
- Which publicly listed bikes were visible, and where were they located?
- Which bikes were marked reserved or disabled in a snapshot?
- How did availability differ between stations or regions in the observed
  snapshots?
- What were the observed availability totals by date and hour?

### Derived metrics

These are calculations from observed fields, with no claim that they represent
trips:

- Bike availability ratio: `num_bikes_available / capacity` where capacity is
  non-null and non-zero.
- Dock share of capacity: `num_docks_available / capacity` under the same
  denominator rule.
- E-bike share of available bikes.
- Empty-station snapshot count and rate.
- Average, minimum, and maximum observed bikes per station.
- Change in a station's observed bike count between two ordered snapshots.
- Snapshot coverage: number of timestamps and stations represented.
- Distribution of publicly visible free bikes by station, vehicle type, or
  coordinates.

A change between snapshots is a state difference. It is not a ride, return,
trip, turnover event, or utilization measurement.

### Proxy metrics

These can be useful operational indicators only when labelled as proxies:

- Low-availability station snapshots, using an explicit threshold such as
  availability ratio <= 0.20.
- Empty-station exposure, measured as the fraction of observed snapshots with
  zero available bikes.
- Availability imbalance, such as the difference between the highest and
  lowest station availability ratio in the same observed system period.
- Possible state transition flags between adjacent observations.

These proxies describe observed operational state. They do not establish
customer demand, unmet demand, or service quality causality.

### Impossible or misleading with current data

Do not create measures for:

- trips, rides, or completed rentals
- trip duration, origin/destination, or route
- revenue, fares paid, or customer counts
- customer behavior or demand
- actual utilization, turnover, rides per bike, or fleet productivity
- station performance interpreted as demand without an authoritative event
  source
- total fleet availability inferred from absence in `free_bike_status`

A bike disappearing from a later free-bike snapshot may mean it is in use, but
could also reflect feed timing, maintenance, reservation, or other state. The
absence is not a trip event.

## 2. Measures to design

The following small measure set is sufficient for a focused report. Names are
suggested Power BI measure names; formulas are conceptual DAX, not code to add
in this design task.

| Measure | Meaning and source | Conceptual formula | Grain/assumptions |
| --- | --- | --- | --- |
| `Total Bikes Available` | Observed station bikes from `FactStationAvailability[num_bikes_available]` | `SUM(num_bikes_available)` | Current filter context; additive across stations within a snapshot context |
| `Total Docks Available` | Observed free docks from `num_docks_available` | `SUM(num_docks_available)` | Snapshot state, not turnover |
| `Total Capacity` | Observed station capacity from `capacity` | `SUM(capacity)` | Capacity is repeated at fact snapshot grain; use station fact only |
| `Station Count` | Number of station rows represented | `DISTINCTCOUNT(station_id)` | Counts represented stations, not necessarily the full registered system |
| `Bike Availability Ratio` | Available bikes relative to observed capacity | `DIVIDE([Total Bikes Available], [Total Capacity])` | Null/zero capacity yields blank; ratio is not utilization |
| `Empty Station Count` | Station snapshots with zero bikes | `COUNTROWS(FILTER(FactStationAvailability, num_bikes_available = 0))` | Count of observed station states |
| `Empty Station Rate` | Share of station snapshots with zero bikes | `DIVIDE([Empty Station Count], COUNTROWS(FactStationAvailability))` | Use the same filter context and denominator policy |
| `Available E-bikes` | Observed e-bike count | `SUM(FactStationVehicleTypeAvailability[count])` filtered to `is_ebike = TRUE` | Vehicle-type fact; do not add to station totals when visual grains overlap |
| `E-bike Share` | E-bikes among available bikes | `DIVIDE([Available E-bikes], [Total Bikes Available])` | Null when total bikes is zero; system Gold also contains this derived value |
| `Visible Free Bikes` | Distinct publicly listed bikes in `FactFreeBikeSnapshot` | `DISTINCTCOUNT(bike_id)` | Visible free bikes only, not total fleet |
| `Low Availability Snapshots` | Operational threshold proxy | Count station fact rows where `DIVIDE(num_bikes_available, capacity) <= 0.20` | Threshold must be labelled and documented as a proxy |
| `Observed Snapshot Count` | Number of distinct system timestamps | `DISTINCTCOUNT(observed_at)` | Feed jitter means source feed timestamps may differ; use Gold system timestamps for system charts |

For station-level average/min/max and empty counts, the existing
`gold_station_availability_metrics` can be used as a hidden validation source,
but report measures should normally calculate from the station fact so date,
hour, and station filters remain meaningful.

`gold_system_availability` already contains system-grain totals and
`ebike_share_of_available_bikes`; it is appropriate for system KPI cards and
system trend charts. Do not combine its totals with station-fact totals in one
visual unless the visual deliberately chooses one source.

## 3. Maximum three-page report

### Page 1: System Availability

**Purpose:** Answer whether the system had observed bikes and docks available
through time.

**KPI cards:**

- Total Bikes Available
- Total Docks Available
- Total Capacity
- Bike Availability Ratio
- E-bike Share

**Visuals:**

- Line chart: `observed_at` by total bikes and total docks from
  `FactSystemAvailability`.
- Column or line chart: total bikes and e-bikes by `hour_of_day`.
- Stacked/clustered chart: available bikes versus docks by date.
- Small detail table: timestamp, station count, total capacity, bikes, docks,
  e-bikes.

**Slicers:** date, weekday/weekend, hour, region identity, vehicle type where
appropriate.

**Interactions:** selecting a date or hour filters the detail table and the
system trend. Avoid mixing station-level facts into the system trend page.

**Important limitation:** the current local sample has one system timestamp;
the time charts become useful only after more scheduled snapshots accumulate.

### Page 2: Station Availability

**Purpose:** Compare observed station conditions and identify low-availability
state, not demand.

**KPI cards:**

- Station Count
- Empty Station Count
- Empty Station Rate
- Average Bike Availability Ratio
- Low Availability Snapshots

**Visuals:**

- Map: station coordinates sized/colored by observed bikes or availability
  ratio for the selected snapshot.
- Ranked bar chart: station name by availability ratio or bikes available.
- Scatter plot: capacity versus average observed bikes, with station name in
  tooltip.
- Detail table: station, region, capacity, bikes, docks, ratio, observed_at,
  renting/returning flags.

**Slicers:** date, hour, station, region, virtual-station flag, renting and
returning status.

**Interactions:** selecting a station filters its detail and the tooltip. A
date/hour selection must filter the station fact, not the all-history station
metrics helper.

**Tooltip/drill-through:** a station tooltip can show latest selected state,
minimum/maximum observed bikes in the current filter context, and empty-state
count. A station drill-through is justified if the collected history becomes
large enough; it should remain a state timeline, not a trip report.

### Page 3: Vehicle and Free-Bike State

**Purpose:** Explain the composition and location of publicly visible bikes.

**KPI cards:**

- Visible Free Bikes
- Available E-bikes
- E-bike Share
- Reserved Visible Bikes
- Disabled Visible Bikes

**Visuals:**

- Stacked column: station/vehicle type count from
  `FactStationVehicleTypeAvailability`.
- Bar chart: visible free bikes by vehicle type.
- Map: free-bike coordinates colored by e-bike/reserved/disabled state.
- Detail table: bike ID, observed_at, station, vehicle type, pricing plan,
  reserved, disabled, fuel/range when present.

**Slicers:** date, hour, station, vehicle type, e-bike flag, reserved/disabled
flags, pricing plan if the hidden pricing helper is later exposed.

**Interactions:** vehicle type selection filters both vehicle-type availability
and free-bike state. Keep station-level totals out of the vehicle-type fact
visual to avoid grain multiplication.

**Limitation:** `free_bike_status` covers publicly visible bikes, not bikes that
may be in use or otherwise absent from the feed.

## 4. Data access strategy

### Direct Parquet

**Advantages:**

- matches the implemented Gold output directly
- no new runtime dependency or database
- preserves the local Raw/Silver/Gold separation
- easy to inspect and reproduce
- suitable for the current small output files

**Costs:**

- Power BI Desktop refresh depends on local file paths
- scheduled Power BI Service refresh would need a gateway or a future hosted
  file location
- Power Query must create identity helper tables and avoid unsafe snapshot
  relationships
- GitHub Actions artifacts are not a durable Power BI source

### DuckDB intermediate layer

**Advantages:**

- convenient SQL over many Parquet files
- could provide a stable database endpoint or views
- useful if Gold grows beyond a comfortable import/query size

**Costs now:**

- DuckDB is not implemented or locked in this repository
- it would add deployment, refresh, and connection decisions without solving a
  current data-volume problem
- Power BI would still need a gateway or accessible hosted database for cloud
  refresh
- it would blur the current simple Gold-as-Parquet contract

### Recommendation for v1

Use direct Gold Parquet import in Power BI Desktop. Import only the recommended
Gold tables, create the identity helper queries in Power Query, and keep the
model Import-based. Treat the local path as a development/portfolio source.
Do not introduce DuckDB for this report. Reconsider it only when file count,
refresh duration, concurrent consumers, or a stable SQL serving requirement
creates a concrete problem.

## 5. Roadmap review and proposed revision

### Inconsistencies in the current roadmap

- Phase 3 marks Docker, Airflow, and an ingestion DAG as incomplete, but the
  implemented project deliberately uses a one-shot Python job plus GitHub
  Actions scheduling. Those technologies are not required by the current
  workload and should remain deferred rather than treated as missing work.
- Phase 3 scheduling, retries, failure handling, and basic monitoring are
  implemented and correctly marked complete.
- Phase 4 marks `Incremental processing` incomplete even though restartable
  incremental Silver/Gold processing and tests are implemented. It should be
  marked complete or renamed to distinguish local incremental processing from
  future dbt incremental models.
- Phase 4 lists DuckDB, dbt, and staging models as planned, but none is
  implemented and the current Python Silver/Gold layers already provide the
  needed transformation contract. They should be deferred, not introduced for
  the sake of the roadmap.
- Phase 4 dimensions, facts, analytical aggregations, and incremental local
  processing are implemented. The documentation should distinguish those
  Python/Parquet models from dbt models.
- Phase 5 is appropriately incomplete, but its first bounded task should be
  review of this design followed by a small Power BI model, not a full platform
  redesign.
- Phase 6 remains the real operational gap: durable retention, backup, and
  reliable long-term collection are not solved by 14-day GitHub artifacts.
- Existing `DATA_MODEL.md` contains older conceptual names such as
  `fact_station_snapshot` and `fact_bike_snapshot`; the implemented Gold names
  in `GOLD_MODEL.md` are authoritative for the future report.

### Proposed revised roadmap

This is a proposal only; `tasks/ROADMAP.md` is intentionally not modified by
this design task.

1. **Foundation:** keep complete.
2. **GBFS ingestion and Raw/Silver:** keep complete.
3. **Lightweight orchestration:** keep scheduling, retries, failure handling,
   and basic run observability complete. Move Docker, Airflow, and ingestion DAG
   to a deferred/future-infrastructure section.
4. **Local analytics engineering:** mark Gold dimensions, facts, aggregations,
   and local incremental processing complete. Keep DuckDB, dbt, dbt staging,
   and dbt tests deferred until scale or SQL-model governance requires them.
5. **Power BI consumption:** design review; build the direct-Parquet semantic
   model; create the measures; build the three-page report; validate the
   snapshot/non-trip messaging. Add Gold relationship keys only if historical
   snapshot slicing is a required acceptance criterion.
6. **Continuous collection and durability:** run a dedicated collector,
   establish retention and backups, replace temporary GitHub artifacts with
   durable storage, and add alerting/operational monitoring.
7. **Future authoritative trip analytics:** only after an authoritative trip
   source is acquired; keep inferred GBFS state transitions separate.

## 6. Current limitations and acceptance criteria

The design is ready for review, not implementation. Before building the report,
confirm:

- whether the first report should use current identity helpers or wait for Gold
  snapshot relationship keys;
- the required collection history and retention period;
- whether Power BI Desktop-only refresh is acceptable for v1;
- whether region and pricing analysis are in scope for the first report;
- that all report labels say `observed`, `available`, or `snapshot` where
  `utilization` or `demand` could otherwise be inferred.
