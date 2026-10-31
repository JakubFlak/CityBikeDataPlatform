# Gold Analytical Model

Gold is a deterministic analytical projection of Silver Parquet. Its tables
represent observed states and are not rides, trips, utilization, or customer
events.

## Time semantics

`observed_at` is the canonical UTC observation timestamp for identity,
ordering, and matching. `observed_at_local` is the same instant converted
using the IANA `Europe/Warsaw` timezone. Gold derives `date_key`,
`hour_of_day`, and the `dim_date` calendar attributes from local time;
midnight and CET/CEST transitions are handled using timezone rules.

## Dimensions

All entity dimensions are snapshot dimensions keyed by entity ID plus UTC
`observed_at`. They preserve attributes as observed rather than applying a
latest-only or SCD Type 2 model.

| Table | Grain |
| --- | --- |
| `dim_station` | Station + `observed_at`. |
| `dim_vehicle_type` | Vehicle type + `observed_at`; includes `is_ebike`. |
| `dim_region` | Region + `observed_at`. |
| `dim_pricing_plan` | Plan + `observed_at`. |
| `dim_pricing_plan_tier` | Plan + tier index + `observed_at`. |
| `dim_date` | Local calendar date represented by Gold facts. |

## Facts and system aggregate

### `fact_station_availability`

**Grain:** one station state per `station_id + observed_at`. It carries
`num_bikes_available`, source dock/capacity fields, status flags,
`last_reported`, and date/region attributes. Power BI currently removes some
lineage columns from its import.

### `fact_station_vehicle_type_availability`

**Grain:** one station, vehicle type, and `observed_at`. It contains the
source count and e-bike classification. It is separate from the station fact
to avoid multiplying station-level measures.

### `fact_free_bike_snapshot`

**Grain:** one publicly listed bike per `bike_id + observed_at`. It contains
location, optional station association, vehicle type, pricing plan, and
state/range attributes. It does not provide authoritative ride history.

### `gold_system_availability`

**Grain:** one system row per distinct `station_status` observation time.
`station_count` counts station-status rows at that observation;
`empty_station_count` counts rows whose `num_bikes_available` is exactly
zero; `available_stations` is `station_count - empty_station_count`.
`available_station_bikes` sums station bike counts, treating null counts as
zero for this sum. E-bike totals sum matching station vehicle-type counts.
Regular bikes are total station bikes minus those e-bike counts.

`available_free_bikes` counts `free_bike_status` rows with a null
`station_id`; these are outside-station observations, not the total number of
bikes at stations. Free-bike observations are matched to the nearest system
observation within five minutes.

These are observed state counts. The model excludes capacity-, dock-,
demand-, utilization-, revenue-, and trip-based KPIs.

## Join and quality behavior

Gold aligns related feed rows to the nearest matching observation within a
five-minute tolerance. Missing entities, duplicate keys, ambiguous nearest
matches, and matches outside the tolerance raise errors. Feed observations
do not need identical timestamps, but their match must be unambiguous and
within tolerance.

Rows are sorted deterministically and output tables are written as a complete
projection from Silver. The incremental coordinator stages and validates the
candidate Gold tables before replacing existing outputs.

## Running Gold transformations

The normal full pipeline is:

```powershell
uv run python scripts/run_pipeline.py
```

For an explicit Gold rebuild from existing Silver:

```powershell
uv run python scripts/transform_to_gold.py
```

The standalone transform is not incremental; it reads `data/silver/*.parquet`
and writes the tables under `data/gold/`. The complete table list and grain
are in [the data model](DATA_MODEL.md); Power BI interpretations are in
[Power BI analytics](POWER_BI_ANALYTICS.md).
