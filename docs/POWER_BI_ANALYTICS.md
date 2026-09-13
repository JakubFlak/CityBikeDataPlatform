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

- How many bikes were available at each station snapshot?
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

- E-bike composition of available bikes.
- Empty-station snapshot count and rate.
- Average, minimum, and maximum observed bikes per station across an explicitly
  selected set of snapshots.
- Change in a station's observed bike count between two ordered snapshots.
- Snapshot coverage: number of timestamps and stations represented.
- Distribution of publicly visible free bikes by station, vehicle type, or
  coordinates.

A change between snapshots is a state difference. It is not a ride, return,
trip, turnover event, or utilization measurement.

### Proxy metrics

These can be useful operational indicators only when labelled as proxies:

- Low-availability station snapshots, using an explicit bike-count threshold.
- Empty-station-snapshot exposure, measured as the fraction of observed
  station snapshots with zero available bikes.
- Availability imbalance, such as the difference between the highest and
  lowest observed bike counts in the same system period.
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

## 2. Snapshot KPI policy

The facts are periodic snapshot facts. A `SUM` across multiple `observed_at`
values is generally a sum of repeated states, not a system total over the
period. The v1 report therefore uses this simple policy:

1. **State KPI cards and point-in-time maps use the latest snapshot in the
  current filter context.** A date/hour/station filter may narrow the context;
  the measure then resolves the maximum available `observed_at` in that
  context.
2. **Snapshot trend visuals place `observed_at` on the axis.** The measure is
  evaluated independently for each timestamp, so each point is a snapshot
  state rather than an accumulation.
3. **Period summary visuals use explicitly named snapshot aggregations.** Use
  `Average ... Per Snapshot`, `Minimum ... Per Snapshot`, `Maximum ... Per
  Snapshot`, or `... Snapshot Count`; never present a raw multi-timestamp sum
  as a current-state KPI.
4. **A visual must declare its grain.** If it cannot show or select the
  timestamp grain, it should use a snapshot aggregation or be removed.

This avoids a card such as `Total Bikes Available = 1,500` when that number is
actually 500 + 520 + 480 from three snapshots. It also keeps the model simple:
no calculation groups or advanced time-intelligence layer is required.

### Measures and behavior across multiple timestamps

The following are conceptual DAX designs, not code to add in this task. The
`Latest Snapshot` pattern means: find the maximum `observed_at` in the current
fact filter context, then evaluate the inner expression only at that timestamp.

| Measure | Single-snapshot meaning | More than one `observed_at` in context | Recommended definition |
| --- | --- | --- | --- |
| `Bikes Available - Latest Snapshot` | Bikes available across the selected stations at one timestamp | Uses the latest timestamp; does not add snapshots | `SUM(num_bikes_available)` after filtering fact rows to latest `observed_at` |
| `Station Count - Latest Snapshot` | Stations represented at one timestamp | Counts distinct stations only at the latest timestamp | `DISTINCTCOUNT(station_id)` at latest timestamp |
| `Empty Station Count - Latest Snapshot` | Stations with zero bikes at one timestamp | Counts empty stations only at latest timestamp | Count station rows where bikes = 0 after latest filter |
| `Empty Station Snapshot Count` | Number of empty station states | Counts empty station rows across all selected timestamps | `COUNTROWS` of station snapshots with bikes = 0; explicitly a state count |
| `Empty Station Snapshot Rate` | Empty station states divided by all station states | Percentage of station snapshots empty across the selected period | `DIVIDE([Empty Station Snapshot Count], [Station Snapshot Count])` |
| `E-bikes Available - Latest Snapshot` | E-bikes reported at one timestamp | Uses latest timestamp; does not add repeated vehicle states | Sum vehicle-type `count` for `is_ebike = TRUE` at latest timestamp |
| `E-bikes Available - Latest Snapshot` | E-bikes reported at one timestamp | Uses latest timestamp; does not add repeated vehicle states | Sum vehicle-type `count` for `is_ebike = TRUE` at latest timestamp |
| `Average Bikes Available Per Snapshot` | Bikes at the selected snapshots | Averages system `available_bikes`, one row per `observed_at` | Average of `FactSystemAvailability[available_bikes]` by timestamp |
| `Minimum Bikes Available Per Snapshot` | Minimum observed system bikes | Minimum system `available_bikes` across selected timestamps | Minimum of system available bikes by timestamp |
| `Maximum Bikes Available Per Snapshot` | Maximum observed system bikes | Maximum system `available_bikes` across selected timestamps | Maximum of system available bikes by timestamp |
| `Visible Bikes - Latest Snapshot` | Distinct publicly visible bikes at one timestamp | Uses latest timestamp, so a bike seen repeatedly is counted once | `DISTINCTCOUNT(bike_id)` after latest timestamp filter |
| `Visible Bike Observations` | One visible-bike row at one timestamp | Counts bike observations across timestamps; the same bike can count repeatedly | `COUNTROWS(FactFreeBikeSnapshot)`; label as observations |
| `Distinct Bikes Observed In Period` | Same as visible bikes for one timestamp | Counts unique bike IDs seen at least once in the period, not simultaneous availability | `DISTINCTCOUNT(bike_id)` across the period; never call this available bikes |
| `Reserved Visible Bikes - Latest Snapshot` | Distinct visible bikes marked reserved at one timestamp | Uses latest timestamp only | Distinct bike count filtered to `is_reserved = TRUE` |
| `Reserved Bike Observations` | Reserved visible-bike rows at one timestamp | Counts reserved observations across timestamps | `COUNTROWS` filtered to reserved; label as observations |
| `Disabled Visible Bikes - Latest Snapshot` | Distinct visible bikes marked disabled at one timestamp | Uses latest timestamp only | Distinct bike count filtered to `is_disabled = TRUE` |
| `Disabled Bike Observations` | Disabled visible-bike rows at one timestamp | Counts disabled observations across timestamps | `COUNTROWS` filtered to disabled; label as observations |
| `Low Availability Station Snapshot Count` | Low-availability station states | Counts station snapshots meeting a declared bike-count threshold | `COUNTROWS` where bikes are below the threshold; proxy, not demand |
| `Observed System Snapshot Count` | One system timestamp | Counts distinct timestamps; does not count station rows | `DISTINCTCOUNT(FactSystemAvailability[observed_at])` |
| `Station Snapshot Count` | One station state | Counts station state rows across selected timestamps | `COUNTROWS(FactStationAvailability)` |

The deprecated `gold_station_availability_metrics` contained all-history
station-level summaries. It is not suitable for date or hour-filtered KPIs
because it has no `observed_at`, so it is not imported. Calculate period
averages/minimums/maximums from the periodic fact or system aggregate, with the
snapshot aggregation stated in the measure name.

`gold_system_availability` is the preferred source for system-level snapshot
state. Do not combine its state counts with station-fact counts in one visual
unless the visual deliberately chooses one source.

## 3. Visual grain rules

Every visual must use one of these declared grains:

- **System snapshot:** one point or row per `FactSystemAvailability[observed_at]`.
- **Station snapshot:** one station state per `station_id + observed_at`.
- **Station/vehicle snapshot:** one station/vehicle state per
  `station_id + vehicle_type_id + observed_at`.
- **Free-bike snapshot:** one bike state per `bike_id + observed_at`.
- **Period aggregation:** one row per selected date/hour/region/vehicle group,
  with an explicit latest, average, minimum, maximum, or snapshot-count
  definition.

Station maps, ranked station bars, and current-state KPI cards must have a
single selected/latest snapshot. If no timestamp is selected, they must use
the latest-snapshot measures, never raw `SUM` across the date range. Free-bike
maps follow the same rule: one point per visible bike at the selected/latest
timestamp. A trend chart may contain multiple snapshots only when
`observed_at` is its axis and its tooltip states the snapshot time.

## 4. Maximum three-page report

### Page 1: System Availability

**Purpose:** Monitor observed system bike availability and empty-station state
through time.

**KPI cards:**

- Bikes Available - Latest Snapshot
- Station Count - Latest Snapshot
- Empty Stations - Latest Snapshot
- Visible Free Bikes - Latest Snapshot
- E-bikes Available - Latest Snapshot

Each card is a **system snapshot** KPI from `FactSystemAvailability` and uses
the latest `observed_at` in the active date/hour context. It must display the
selected/latest timestamp in a subtitle or tooltip.

**Visuals:**

- Line chart, grain **system snapshot**: one point per `observed_at`, showing
  `available_bikes`, `empty_station_count`, and `available_ebikes` from
  `FactSystemAvailability`. This is a per-snapshot state trend, not a sum over
  the selected period.
- Column chart, grain **period aggregation by hour**: average system bikes and
  empty stations per snapshot grouped by `hour_of_day`. Label the values as
  averages, not totals.
- Detail table, grain **system snapshot**: timestamp, station count, available
  bikes, empty stations, visible free bikes, and e-bikes. Do not use a card or
  chart that hides timestamp grain while summing this table.

**Slicers:** date, weekday/weekend, and hour. Region and vehicle-type slicers
belong on the station and vehicle pages; they do not filter the already
system-aggregated `FactSystemAvailability` in the v1 model.

**Interactions:** selecting a date or hour filters the detail table and the
system trend. Avoid mixing station-level facts into the system trend page.

**Important limitation:** the current local sample has one system timestamp;
the time charts become useful only after more scheduled snapshots accumulate.

### Page 2: Station Availability

**Purpose:** Compare observed station conditions and identify low-availability
state, not demand.

**KPI cards:**

- Station Count - Latest Snapshot
- Empty Stations - Latest Snapshot
- Empty Station Snapshot Rate
- Average Bikes Available Per Snapshot
- Low Availability Station Snapshot Count

The first two are **station snapshot** state KPIs at the latest timestamp.
The rate and low-availability count are explicitly named state/period metrics;
their subtitle must state whether the context contains one timestamp or a
period.

**Visuals:**

- Map, grain **station snapshot**: one point per station at the selected/latest
  `observed_at`, sized by observed bikes available and marked when empty.
- Ranked bar chart, grain **station snapshot**: one bar per station at the
  selected/latest timestamp, ranked by observed bikes available.
- Scatter plot, grain **station period aggregation**: one point per station,
  with average bikes per snapshot on one axis and empty-state count on the
  other. The title must say `Average Bikes Per Snapshot`; it must not imply
  current state.
- Detail table, grain **station snapshot**: station, region, bikes,
  `observed_at`, and renting/returning flags.

**Slicers:** date, hour, station, region, virtual-station flag, renting and
returning status.

**Interactions:** selecting a station filters its detail and the tooltip. A
date/hour selection must filter the station fact, not the all-history station
metrics helper.

**Tooltip/drill-through:** a station tooltip can show the latest selected
station state plus explicitly labelled minimum/maximum bikes per snapshot and
empty station snapshot count for the selected period. A station drill-through
is justified if the collected history becomes large enough; it should remain a
station-state timeline, not a trip report.

### Page 3: Vehicle and Free-Bike State

**Purpose:** Compare observed vehicle composition and the spatial state of
publicly visible bikes. This page is not a pricing or miscellaneous metadata
page.

**KPI cards:**

- Visible Bikes - Latest Snapshot
- E-bikes Available - Latest Snapshot
- E-bike Share - Latest Snapshot
- Reserved Visible Bikes - Latest Snapshot
- Disabled Visible Bikes - Latest Snapshot

**Visuals:**

- Stacked column, grain **station/vehicle snapshot**: count by vehicle type
  for the selected/latest timestamp. Do not sum vehicle rows from multiple
  timestamps into a current-state visual.
- Bar chart, grain **vehicle-type snapshot**: latest visible-bike count by
  vehicle type, with a separate tooltip for `Distinct Bikes Observed In
  Period` when a period is intentionally selected.
- Map, grain **free-bike snapshot**: one point per visible bike at the
  selected/latest timestamp, colored by e-bike/reserved/disabled state.
- Detail table, grain **free-bike snapshot**: bike ID, `observed_at`, station,
  vehicle type, reserved, disabled, and optional fuel/range. Pricing plan is
  supporting context, not a page-level analytical focus.

**Slicers:** date, hour, station, vehicle type, e-bike flag, reserved/disabled
flags, pricing plan if the hidden pricing helper is later exposed.

**Interactions:** vehicle type selection filters both vehicle-type availability
and free-bike state. Keep station-level totals out of the vehicle-type fact
visual to avoid grain multiplication. All current-state cards and the map use
the same selected/latest timestamp policy.

**Limitation:** `free_bike_status` covers publicly visible bikes, not bikes that
may be in use or otherwise absent from the feed.

## 5. Data access strategy

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

## 6. Roadmap review and proposed revision

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

## 7. Current limitations and acceptance criteria

The design is ready for review, not implementation. Before building the report,
confirm:

- whether the first report should use current identity helpers or wait for Gold
  snapshot relationship keys;
- the required collection history and retention period;
- whether Power BI Desktop-only refresh is acceptable for v1;
- whether region and pricing analysis are in scope for the first report;
- that all report labels say `observed`, `available`, or `snapshot` where
  `utilization` or `demand` could otherwise be inferred.
