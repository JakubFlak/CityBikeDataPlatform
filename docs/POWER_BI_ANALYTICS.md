# Power BI Analytics and KPI Semantics

## Scope and snapshot interpretation

The Power BI model is built on observed GBFS snapshots. It does not contain
authoritative trips, demand, revenue, customers, or utilization. A state
change between snapshots is not a trip event.

Gold's central station fact has grain `station_id + observed_at`. The system
aggregate has one row per station-status observation timestamp. Free-bike
facts have grain `bike_id + observed_at`. Adding values across timestamps
usually adds repeated observed states; it does not produce a current system
total unless the measure selects one timestamp.

`observed_at` is UTC and remains the observation identity. `observed_at_local`
is the same instant expressed in `Europe/Warsaw` for local presentation and
calendar axes. Feed retrieval is sequential: all six feed records from one
collection cycle do not necessarily share an exact timestamp. Gold aligns
dependent observations to a nearest timestamp within five minutes and rejects
missing, ambiguous, or out-of-tolerance matches. System rows are keyed by
station-status time; free-bike rows outside stations are attributed to the
nearest such observation.

## KPI catalogue

The definitions below follow the measures in
`dashboard/Dashboard.SemanticModel/definition/tables/_Measures.tmdl` and the
Gold generation in `src/bike_data/gold.py`. Filter context matters: report
date, period, grain, region, and station selections affect measures where the
model relationships permit those filters.

| Report measure | Definition and calculation | Unit / interpretation | Important limitations |
| --- | --- | --- | --- |
| `Available station bikes - latest` | Finds the maximum `gold_system_availability[observed_at_local]` in the current filter context and returns `MAX(available_station_bikes)` at that timestamp. Gold sums `station_status.num_bikes_available` across observed station rows. | Bikes reported at stations in one selected/latest system snapshot. | Not a trip count or a period sum. Null station bike counts contribute zero to the Gold total. Latest uses a local, timezone-naive timestamp. |
| `Available free bikes - latest` | At the maximum system `observed_at_local` in the current context, returns `MAX(available_free_bikes)`. Gold counts `free_bike_status` rows with null `station_id`, matched to a system observation. | Bikes reported outside stations in that snapshot. | This is not the number of bikes docked at stations and not a fleet-wide total. Not evidence of trips or usage. |
| `Stations - latest` | Finds maximum system `observed_at` (UTC) in context and returns `station_count` at that timestamp. | Number of station-status rows represented in one snapshot. | Missing station records are not synthesized into the denominator. This latest measure uses UTC, unlike some bike latest measures that use local time. |
| `Empty Stations - latest` | At maximum system `observed_at` in context, returns the aggregate `empty_station_count`. Gold counts station rows whose `num_bikes_available` is exactly zero. | Count of observed station rows with zero reported bikes. | A station with no record is not an empty station. Null bike counts are not counted as exactly zero. |
| `Station Availability %` | `SUM(available_stations) / SUM(station_count)` over the selected system observations. At each timestamp Gold calculates `available_stations = station_count - empty_station_count`. | Share of represented station observations treated as available in the selected system snapshots. | Across a period this is a ratio of summed observations, weighted by station-row counts per snapshot, not an average of timestamp percentages or elapsed-time availability. Gold's subtraction treats null bike counts as non-empty; see caveat below. |
| `Station Availability Rate` | On `fact_station_availability`, counts rows with `num_bikes_available > 0` and divides by `Station Snapshot Count` (`COUNTROWS` of station fact rows). | Share of observed station-state rows with more than zero bikes; for one timestamp, share of represented station rows available. | Across a period it is an observation-weighted rate, not percent of elapsed time. Null-count rows remain in the denominator but not the positive numerator. |
| `Empty Station Observation Rate` | `Empty Observation Count / Station Snapshot Count`; empty means exactly `num_bikes_available = 0`. | Share of observed station-state rows classified as empty. | Not percentage of time empty. No station row means no observation and does not enter numerator or denominator. |
| `Average Bikes per Station Observation` | DAX `AVERAGE(fact_station_availability[num_bikes_available])` across station fact rows in the current context. Each non-blank station observation has equal weight. | Mean reported bikes per station observation. | Not an average of unique stations or station maxima. Stations represented in more snapshots contribute more rows; blanks are ignored by `AVERAGE`. |
| `Available e-bikes` | `SUM(gold_system_availability[available_station_ebikes])` over the current context. The Gold value sums station-status vehicle-type counts classified as e-bikes. | E-bikes reported at stations, summed over selected system snapshots. | Across multiple timestamps, the same state is counted repeatedly. Not latest unless the visual/filter context is one timestamp. Does not include free bikes outside stations. |
| `Available regular bikes` | `SUM(gold_system_availability[available_station_regular_bikes])` over the current context. Gold calculates it as total station bikes minus station e-bikes. | Non-e-bike station availability by snapshot, summed over the selected context. | Across multiple timestamps this is a sum of repeated states. It is derived, not a separately classified vehicle count. |
| `Ebike share` | `Available e-bikes / (Available e-bikes + Available regular bikes)` using the two sums above. | E-bike share of station-bike observations in the current context. | On one timestamp it is a composition ratio for that state. Over a period it is a ratio of sums, not the mean of per-snapshot shares. It excludes free bikes outside stations and depends on source `propulsion_type` classification. |
| `Available regular station bikes - latest` | At the maximum `observed_at_local`, returns the Gold regular-bike value. | Non-e-bike station count in one latest/selected system snapshot. | Local naive timestamp determines latest. |
| `Available regular station ebikes - latest` | Despite its name, its DAX returns `available_station_ebikes` at maximum `observed_at_local`. | The result is an e-bike count, not regular bikes. | The name is inconsistent with the expression and may mislabel the Bikes Analysis donut. It is documented, not silently corrected here. |
| `Average Free Bikes Outside Stations` | Iterates distinct `fact_free_bike_snapshot[observed_at]` values; counts rows with blank `station_id` at each time and averages those counts. | Average outside-station bike rows per represented free-bike observation timestamp. | Not a count of distinct bikes over a period. The imported free-bike fact is filtered in Power Query to latitudes 51 through 51.23 and vehicle IDs `183` or `71`, so this measure may reflect that filtered import rather than all source rows. |

### Availability and missing observations

The station fact contains one row per station state that was actually present
in `station_status`. A missing row does not imply zero availability and is
not counted as an empty station. In the Gold system aggregate, a row is empty
only when its bike count equals zero. `available_stations` is calculated as
all station rows minus those exact-zero rows; consequently a row whose bike
count is null is counted as non-empty by that aggregate. The station-level
`Station Availability Rate`, by contrast, counts only values greater than
zero as available while retaining all station rows in its denominator.

The table schemas allow nullable source values, so these two availability
measures can differ if null counts occur. No DAX or pipeline semantics have
been changed as part of this documentation task. Whether null station counts
should be excluded from denominators is an unresolved model decision.

### E-bike classification

Gold marks a vehicle type as e-bike when the lowercased
`propulsion_type` is `electric` or `electric_assist`. System e-bike counts
come from `station_status.vehicle_types_available` rows classified by the
matching vehicle type observation. The report's share denominator is the
sum of e-bike and regular station-bike counts, not all bikes in
`free_bike_status`. It is therefore a snapshot composition proxy, not fleet
composition or usage.

## Period and Grain selector

`Date Period Selector` is a calculated table containing Current/Previous
Day, Week, Month, and Year periods, anchored to the maximum date in
`dim_date`. Its `Date` relationship filters `dim_date`; `Period` and `Grain`
select date ranges and categories. They do not change the underlying fact
grain, interpolate missing dates, resample snapshots, or alter measure
formulas. Local `date_key` and `hour_of_day` are derived from
`observed_at_local`; a trend point remains an observed timestamp when that
timestamp is on the axis.

The report's System Overview also has a timestamp range slicer. Keep the
selected period in mind: latest measures resolve the maximum timestamp inside
the current date/hour filter context rather than necessarily the latest file
in the repository.

## Pages in the current report

### System Overview

Shows latest station bike count, outside-station free bikes, station count,
and empty stations; system availability over local observation time; and a
station-bike composition donut. The trend uses snapshot timestamps, not a
period sum. The donut includes the measure named
`Available regular station ebikes - latest`, whose expression actually
returns the e-bike count.

### Station Analysis

Compares station-level availability rates over the selected time context,
using a map, time trend, station comparison, and station table. Region,
station, period, and grain selectors filter the station-level context where
relationships allow. `Station Availability Rate` is the proportion of
observed station rows with positive bike counts; its meaning changes from a
single-snapshot share to a period observation rate when several timestamps
are selected.

### Bikes Analysis

Shows e-bike share and average outside-station bike observations, trends for
station regular/e-bike totals and outside-station bikes, plus a bike map.
The map uses the Power Query-filtered free-bike fact (latitude range 51–51.23
and vehicle IDs `183` and `71`); do not read it as an unfiltered full-fleet
map. Series shown across multiple timestamps are snapshot values.
