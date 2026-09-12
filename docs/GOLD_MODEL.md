# Gold Analytical Model

The Gold layer is a deterministic analytical projection of Silver Parquet tables.
It preserves snapshot semantics: `observed_at` is the authoritative UTC
observation timestamp, while provider `last_updated` and Silver lineage remain
available in the source layer. A row observed twice is two states, not a trip.

## Supported analytical questions

The model supports:

- system and station bikes, docks, capacity, and availability over time
- station-level empty-state and availability-ratio indicators
- availability by date, weekday/weekend, and hour of day
- e-bike counts and e-bike share of observed available bikes
- station and free-bike geographic distribution
- availability comparisons by region
- pricing-plan configuration associated with free-bike snapshots
- vehicle-type availability at a station and time

The model does not support rides, trip duration, origin/destination flows,
revenue, customer behavior, actual utilization, or authoritative turnover.
Changes between snapshots can be reported, but they do not prove a rental or
return. Absence from `free_bike_status` is not proof that a bike started a trip.

## Dimensions

All entity dimensions are **snapshot dimensions**, with a composite business key
of entity identifier plus `observed_at`. This is a simple temporal approach: it
preserves changing station capacity, coordinates, names, regions, vehicle
metadata, and pricing configuration without implementing SCD Type 2 surrogate
keys. A future curated current-state view can select the latest row explicitly.

| Table | Grain | Key attributes |
| --- | --- | --- |
| `dim_station` | station + observed_at | name, coordinates, region, capacity, virtual flag |
| `dim_vehicle_type` | vehicle type + observed_at | form factor, propulsion, range, `is_ebike` |
| `dim_region` | region + observed_at | region name |
| `dim_pricing_plan` | plan + observed_at | name, currency, base price, tax flag |
| `dim_pricing_plan_tier` | plan + tier index + observed_at | start, interval, rate, end |
| `dim_date` | calendar date | year, quarter, month, ISO week, weekday, weekend flag |

`dim_date` is generated only for dates present in the facts. `hour_of_day` is a
small integer on facts because a separate time dimension would add no useful
attributes yet. The timestamp itself always remains available.

## Facts

### `fact_station_availability`

**Grain:** station + observed_at. This is the central periodic snapshot fact.

Measures and attributes are `num_bikes_available`, `num_docks_available`,
`capacity`, `is_installed`, `is_renting`, `is_returning`, and `last_reported`.
Foreign keys are the temporal station key (`station_id`, `observed_at`),
`region_id` from the matching station snapshot, and `date_key`.

Station-level measures are not repeated once per vehicle type. Ratios are not
stored here: they can be calculated from these direct measures with explicit
zero/null denominator handling.

### `fact_station_vehicle_type_availability`

**Grain:** station + vehicle_type + observed_at. It contains the source
`count` and `is_ebike`, with temporal station and vehicle-type foreign keys.
Keeping it separate preserves grain clarity and prevents many-to-many
multiplication of station measures.

### `fact_free_bike_snapshot`

**Grain:** bike + observed_at. It contains location, station association,
vehicle type, pricing plan, reserved/disabled state, and optional range/fuel
measures. A bike can occur in many snapshots. This fact enables spatial
availability and state analysis, but it is not a trip or movement fact.

## Derived Gold models

### `gold_system_availability`

**Grain:** observed_at. It aggregates station snapshots into station count,
total capacity, total bikes, total docks, total e-bikes, and e-bike share. The
share is `total_ebikes_available / total_bikes_available` when the denominator
is positive; otherwise it is null.

### `gold_station_availability_metrics`

**Grain:** station across all processed snapshots. It contains snapshot count,
average/minimum/maximum bikes, empty-snapshot count, and average availability
ratio. The ratio is `num_bikes_available / capacity` only where capacity is
present and non-zero. These are reusable descriptive metrics, not utilization.
Presentation-specific aggregations remain out of scope.

## Temporal and quality rules

- Every fact and snapshot dimension is keyed with `observed_at`.
- Gold performs nearest temporal joins between feeds within a five-minute
  tolerance because one collection cycle can produce slightly different
  `observed_at` values per feed. Missing entities, duplicate keys, and matches
  outside that tolerance fail the transform rather than silently mismatching
  states.
- Duplicate dimension keys and missing temporal foreign keys fail the transform.
- Outputs are sorted and overwritten deterministically, so rerunning the same
  Silver inputs produces identical Parquet tables.
- Counts are observed availability counts. They are not transaction counts.

## Transformation

```text
python scripts/transform_to_gold.py
```

The command reads `data/silver/*.parquet` and writes runtime-generated tables
under `data/gold/`. No dbt, DuckDB, cloud storage, orchestration, or BI model
is introduced by this layer.
