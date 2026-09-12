# Silver/Staging Model

This document defines the implemented boundary between raw GBFS snapshots and
future analytical models. Silver reads only the canonical `data_json` payload
from raw Parquet. `source_payload_json` remains an audit representation and is
not parsed by the Silver transformation.

## Lineage and temporal semantics

Every Silver row carries `feed_name`, `source_url`, and `observed_at`. The
`observed_at` value is parsed as timezone-aware input, normalized to UTC, and
written as a UTC-normalized Parquet `timestamp[us]`. The physical timestamp is
timezone-naive for portable reads with the project's current `pyarrow` runtime;
the documented semantic timezone is UTC. It is the application observation
time, not the provider's `last_updated` time.
The provider `last_updated` value is retained as an integer on every base table
and child table where it describes the source snapshot.

Silver preserves every source snapshot. For repeated reference feeds, the
business key includes `observed_at`; no current-state deduplication occurs.

## Tables

### `silver_vehicle_types`

Grain: one vehicle type from one source snapshot.

Business key: `vehicle_type_id + observed_at`.

Columns: `vehicle_type_id` (string), `observed_at` (timestamp UTC),
`feed_name` (string), `source_url` (string), `last_updated` (int64), `name`
(string), `form_factor` (string), `propulsion_type` (string),
`rider_capacity` (int64), `max_range_meters` (int64), `vehicle_image` (string),
`description` (string).

### `silver_station_information`

Grain: one station metadata record from one source snapshot.

Business key: `station_id + observed_at`.

Columns: `station_id` (string), `observed_at` (timestamp UTC), `feed_name`,
`source_url`, `last_updated`, `name` (string), `short_name` (string), `lat`
(float64), `lon` (float64), `region_id` (string), `capacity` (int64),
`is_virtual_station` (bool), `rental_uris_json` (string).

`rental_uris` remains a controlled JSON column because it contains access URLs,
not an independently useful analytical entity. The original nested object is
preserved without flattening.

### `silver_station_status`

Grain: one station state from one source snapshot.

Business key: `station_id + observed_at`.

Columns: `station_id` (string), `observed_at` (timestamp UTC), `feed_name`,
`source_url`, `last_updated`, `last_reported` (int64),
`num_bikes_available` (int64), `num_docks_available` (int64),
`is_installed` (bool), `is_renting` (bool), `is_returning` (bool).

### `silver_station_status_vehicle_types`

Grain: one vehicle type availability count for one station and source
snapshot.

Business key: `station_id + vehicle_type_id + observed_at`.

Columns: `station_id` (string), `vehicle_type_id` (string), `observed_at`
(timestamp UTC), `feed_name`, `source_url`, `last_updated`, `count` (int64).

This normalized child table preserves `vehicle_types_available` and supports
queries such as e-bike availability at a station and time. It references
`silver_station_status` by `station_id + observed_at` and
`silver_vehicle_types` by `vehicle_type_id` within the corresponding source
observation.

### `silver_free_bike_status`

Grain: one publicly available bike state from one source snapshot.

Business key: `bike_id + observed_at`.

Columns: `bike_id` (string), `observed_at` (timestamp UTC), `feed_name`,
`source_url`, `last_updated`, `station_id` (string), `vehicle_type_id`
(string), `pricing_plan_id` (string), `lat` (float64), `lon` (float64),
`is_reserved` (bool), `is_disabled` (bool), `current_fuel_percent`
(float64), `current_range_meters` (int64), `rental_uris_json` (string).

Bike `rental_uris` is retained as controlled JSON for the same access-metadata
reason as station `rental_uris`; no separate URL table is introduced.

### `silver_system_pricing_plans`

Grain: one pricing plan from one source snapshot.

Business key: `plan_id + observed_at`.

Columns: `plan_id` (string), `observed_at` (timestamp UTC), `feed_name`,
`source_url`, `last_updated`, `name` (string), `currency` (string), `price`
(float64), `is_taxable` (bool), `description` (string).

### `silver_system_pricing_plan_tiers`

Grain: one `per_min_pricing` tier for one plan and source snapshot.

Business key: `plan_id + tier_index + observed_at`.

Columns: `plan_id` (string), `tier_index` (int64), `observed_at` (timestamp
UTC), `feed_name`, `source_url`, `last_updated`, `start` (int64), `interval`
(int64), `rate` (float64), `end` (int64).

The tier index preserves source order. A plan's pricing tiers are therefore
relational and queryable without discarding the original pricing structure.

### `silver_system_regions`

Grain: one region from one source snapshot.

Business key: `region_id + observed_at`.

Columns: `region_id` (string), `observed_at` (timestamp UTC), `feed_name`,
`source_url`, `last_updated`, `name` (string).

## Out of scope

This is staging only. No facts, dimensions, KPIs, trip inference, Gold models,
dbt models, DuckDB database, or BI model are created here. Fields not selected
for the typed Silver columns remain available in raw Parquet for later review;
the transformation does not invent values for omitted GBFS fields.

## Running the transformation

The repeatable local transformation command is:

```text
python scripts/transform_to_silver.py
```

It reads every `data/raw/**/*.parquet` file and overwrites the deterministic
table files under `data/silver/`. The output directory is runtime-generated and
ignored by Git. Re-running the command over the same raw files produces the
same table rows and schemas.