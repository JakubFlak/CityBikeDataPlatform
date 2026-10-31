# Power BI Semantic Model

## Open and refresh locally

1. Install the project dependencies with `uv sync --locked --dev`.
2. From the repository root, run `uv run python scripts/run_pipeline.py`.
3. Open `dashboard/Dashboard.pbip` in Power BI Desktop.
4. Refresh the model.

The Power Query expressions in
`dashboard/Dashboard.SemanticModel/definition/expressions.tmdl` and table
definitions use absolute `File.Contents` paths rooted at
`C:\Users\WIZBOX\Desktop\Projects\CityBikeDataPlatform\data\gold`. Refresh
on another checkout or computer requires changing these paths. The Power BI
project is not portable by cloning alone.

## Imported Gold model

The semantic model imports Gold, not Raw or Silver. Its core tables are:

| Table | Role | Grain |
| --- | --- | --- |
| `dim_date` | Calendar dimension. | One local calendar date. |
| `dim_station_identity` | Power Query current-identity helper. | One descriptive station identity. |
| `dim_vehicle_type_identity` | Power Query current-identity helper. | One descriptive vehicle identity. |
| `dim_region_identity` | Power Query current-identity helper. | One descriptive region identity. |
| `fact_station_availability` | Central station snapshot fact. | Station + UTC `observed_at`. |
| `fact_station_vehicle_type_availability` | Child vehicle-count fact. | Station + vehicle type + UTC `observed_at`. |
| `fact_free_bike_snapshot` | Visible-bike snapshot fact. | Bike + UTC `observed_at`. |
| `gold_system_availability` | Pre-aggregated system fact. | One station-status observation timestamp. |
| `_Measures` | DAX measures. | No physical fact grain. |
| `Date Period Selector` | Calculated date-period table. | Date + period + grain category. |

The underlying snapshot dimensions (`dim_station`, `dim_vehicle_type`, and
`dim_region`) remain present for shaping/lineage, but the report uses
single-identity helper tables for its stable-ID slicers. Those helpers take
latest descriptive values and do not provide historically versioned labels.
Pricing dimensions are not central to the three-page report.

Gold facts retain `observed_at` in UTC and `observed_at_local` for local
presentation. `dim_date` relates to facts through `date_key`. Station,
region, and vehicle identity helpers filter facts by entity IDs. The
system-level aggregate is not related to station or region because it is
already at system/timestamp grain. Do not join snapshot dimensions to facts
only on entity ID or bridge facts together; that would create ambiguous or
duplicated results.

## Power Query shaping and report filters

Power Query removes `capacity`, `num_docks_available`, and `is_installed`
from the imported station fact. It removes reserved/disabled/fuel/range
columns from the imported free-bike fact and filters that fact to latitudes
51–51.23 and vehicle IDs `183` and `71`. The map and DAX measures based on
this imported table should be understood in that limited scope.

The report's `Date Period Selector` contains Current/Previous Day, Week,
Month, and Year date ranges anchored to the maximum `dim_date` date. It
filters the date dimension; it does not alter fact grain or automatically
choose an aggregation formula. A visual with multiple timestamps still
contains multiple observed states.

## Snapshot measure rules

`observed_at` is the correct UTC observation identity and chronology.
`observed_at_local` supports local presentation. Latest measures in the
current DAX are not all consistent: some use maximum local timestamp and
others use maximum UTC timestamp. Local timestamps are timezone-naive and
cannot disambiguate both occurrences of a repeated local time at the autumn
DST transition.

The model has several snapshot and period measures with different
denominators and null behavior. In particular, `Station Availability %` and
`Station Availability Rate` are not interchangeable. The measure named
`Available regular station ebikes - latest` returns an e-bike field. These
definitions and the exact implementation are documented in
[Power BI analytics](POWER_BI_ANALYTICS.md).

## Pages

The current report pages are:

1. **System Overview** — latest system snapshot cards, availability trend,
   and station-bike composition.
2. **Station Analysis** — station availability map/trend/comparison and
   station-level measures over selected periods.
3. **Bikes Analysis** — station vehicle-type trends, e-bike share,
   outside-station bike averages, and a filtered bike map.

Page calculations reflect the actual measure expressions, not merely visual
labels. For example, an aggregate over several selected timestamps is a sum
of snapshot observations unless its DAX explicitly selects one timestamp or
averages the intended snapshot grain.

## Not implemented

The semantic model has no trip fact, demand or utilization measures, cloud
refresh configuration, parameterized Gold paths, or deployment automation.
Historical station and other entity labels use latest-identity helpers
rather than exact temporal surrogate keys. See
[the architecture](ARCHITECTURE.md) and
[v2.0 roadmap](../tasks/ROADMAP.md).
