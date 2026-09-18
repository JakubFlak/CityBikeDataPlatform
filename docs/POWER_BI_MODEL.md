# Power BI Semantic Model Design

## Status and scope

This document is a design for a future Power BI model. It does not create a
`.pbix` file, change Parquet schemas, or add a new transformation engine.
The design is based on the implemented Gold layer and its snapshot semantics.

The current generated sample contains one collection cycle: 273 station
availability rows, 2,869 free-bike snapshot rows, 352 station/vehicle rows,
and one row in `gold_system_availability`. Tests cover multiple timestamps and
feed timestamp jitter, but a useful time-series report requires more collected
snapshots than the current local sample contains.

## Modeling principles

- A row is a state observed at a timestamp, not a trip or transaction.
- Gold is the only analytical layer exposed to the report.
- Silver and Raw remain engineering/debugging layers.
- `observed_at` remains available in every snapshot fact as the canonical UTC
   timestamp.
- `observed_at_local` is a planned Gold presentation column; it is not present
   in the currently generated Parquet export or the current report definition.
- Counts are availability counts, not ride counts or utilization.
- Snapshot dimensions are not joined to facts by entity ID alone.

## Snapshot semantic contract

The fact tables are periodic state facts, not additive event facts. Their
numeric columns describe a state at `observed_at` and must not be summed across
timestamps and presented as a current state. This applies to bikes,
vehicle-type counts, and free-bike rows. Capacity and dock fields remain in
the source facts for lineage, but are excluded from Power BI-facing metrics.

The v1 semantic model uses three explicit consumption modes:

1. **Latest-state mode:** KPI cards, maps, and ranked current station visuals
   resolve the maximum `observed_at` in the active filter context. They show one
   state, not a period total.
2. **Per-snapshot mode:** trend tables and lines retain `observed_at` as their
   grain. Each point is one system, station, station/vehicle, or bike state.
3. **Period-summary mode:** period visuals use explicitly named averages,
   minimums, maximums, or snapshot counts. A raw `SUM` across timestamps is not
   a valid generic KPI for these facts.

The model should expose these meanings in measure names and visual subtitles.
`observed_at` remains visible in detail tables and tooltips even when a latest
snapshot measure is used.

## Tables and roles

### Recommended report tables

| Report table | Gold source | Role | Grain | Important columns | Purpose |
| --- | --- | --- | --- | --- | --- |
| `DimDate` | `dim_date` | Dimension | One calendar date | `date_key`, `calendar_date`, `year`, `month`, `week`, `day_name`, `is_weekend` | Date slicing and calendar labels |
| `DimStationIdentity` | latest rows from `dim_station` | Helper dimension | One current identity row per `station_id` | `station_id`, `name`, `short_name`, `lat`, `lon`, `region_id`, `is_virtual_station` | Safe station slicers and map labels without duplicate snapshot IDs |
| `DimVehicleTypeIdentity` | latest rows from `dim_vehicle_type` | Helper dimension | One current identity row per `vehicle_type_id` | `vehicle_type_id`, `name`, `form_factor`, `propulsion_type`, `is_ebike` | Vehicle type and e-bike slicing |
| `DimRegionIdentity` | latest rows from `dim_region` | Helper dimension | One current identity row per `region_id` | `region_id`, `name` | Region slicing for current labels |
| `FactStationAvailability` | `fact_station_availability` | Periodic snapshot fact | One station state per `station_id + observed_at` | `station_id`, `observed_at`, `date_key`, `hour_of_day`, `region_id`, `num_bikes_available`, status flags | Central operational availability fact |
| `FactStationVehicleTypeAvailability` | `fact_station_vehicle_type_availability` | Child periodic fact | One station/vehicle state per `station_id + vehicle_type_id + observed_at` | IDs, `observed_at`, `date_key`, `hour_of_day`, `count`, `is_ebike` | Vehicle-type availability without repeating station measures |
| `FactFreeBikeSnapshot` | `fact_free_bike_snapshot` | Periodic state fact | One publicly listed bike per `bike_id + observed_at` | IDs, `observed_at`, station and coordinates, reserved/disabled flags, fuel/range | Available-bike inventory and spatial state analysis |
| `FactSystemAvailability` | `gold_system_availability` | Aggregate periodic fact | One system aggregate per `observed_at` | `observed_at`, `date_key`, `hour_of_day`, `station_count`, `empty_station_count`, `available_stations`, `available_station_bikes`, `available_station_ebikes`, `available_station_regular_bikes`, `available_free_bikes` | Fast system state and trend visuals |

`DimStationIdentity`, `DimVehicleTypeIdentity`, and `DimRegionIdentity` are
Power Query helper queries created from Gold imports by retaining the latest
row per stable ID. They are not new files or new source tables. They avoid
many-to-many relationships caused by the snapshot dimensions.

### Imported but hidden/supporting tables

| Gold source | Recommended treatment | Reason |
| --- | --- | --- |
| `dim_station` | Hidden | Snapshot rows are useful lineage, but the current fact schema does not expose an exact station snapshot foreign key. |
| `dim_vehicle_type` | Hidden | Same snapshot-dimension issue; use the identity helper for report slicing. |
| `dim_region` | Hidden | Keep for lineage and future historical relationship keys. |
| `dim_pricing_plan` | Hidden | Pricing is source context for free-bike snapshots, not a current report focus. |
| `dim_pricing_plan_tier` | Hidden | Pricing child detail is not needed for the three-page availability report. |
| `gold_station_availability_metrics` | Deprecated and not imported | Its all-history station grain has no timestamp and cannot safely support date/hour filtering. Recompute named period summaries from `FactStationAvailability`. |

Silver tables should not be exposed to report authors. They contain lineage,
implementation details, JSON fields, and child-table structures that are useful
for engineering but would make the semantic model ambiguous.

## Relationships

### Safe v1 relationships

All relationships are one-to-many, single-direction from dimension/helper to
fact, and active unless stated otherwise:

| From | To | Key | Cardinality | Filter direction |
| --- | --- | --- | --- | --- |
| `DimDate[date_key]` | `FactStationAvailability[date_key]` | `date_key` | 1:* | Single |
| `DimDate[date_key]` | `FactStationVehicleTypeAvailability[date_key]` | `date_key` | 1:* | Single |
| `DimDate[date_key]` | `FactFreeBikeSnapshot[date_key]` | `date_key` | 1:* | Single |
| `DimDate[date_key]` | `FactSystemAvailability[date_key]` | `date_key` | 1:* | Single |
| `DimStationIdentity[station_id]` | `FactStationAvailability[station_id]` | `station_id` | 1:* | Single |
| `DimStationIdentity[station_id]` | `FactStationVehicleTypeAvailability[station_id]` | `station_id` | 1:* | Single |
| `DimStationIdentity[station_id]` | `FactFreeBikeSnapshot[station_id]` | `station_id` | 1:* | Single |
| `DimVehicleTypeIdentity[vehicle_type_id]` | `FactStationVehicleTypeAvailability[vehicle_type_id]` | `vehicle_type_id` | 1:* | Single |
| `DimVehicleTypeIdentity[vehicle_type_id]` | `FactFreeBikeSnapshot[vehicle_type_id]` | `vehicle_type_id` | 1:* | Single |
| `DimRegionIdentity[region_id]` | `FactStationAvailability[region_id]` | `region_id` | 1:* | Single |

The identity dimensions deliberately represent the latest known descriptive
attributes. Historical facts retain their observed `region_id`, station ID,
and vehicle type ID, but a later rename or move would be labelled with the
latest identity attribute. This is acceptable for a v1 operational report only
if the report documents that limitation.

The helper relationships do not define snapshot identity. They are descriptive
filters by stable entity ID. A measure that needs a point-in-time result must
still apply the latest `observed_at` policy on the relevant fact; a date
relationship alone intentionally permits multiple snapshots in context.

`FactSystemAvailability` has no station relationship. It is already aggregated
at system/timestamp grain and should be filtered by date and hour only.

`FactFreeBikeSnapshot[station_id]` is nullable, so the station relationship
must allow unmatched/null fact rows. A missing station association is a source
state, not a data-quality reason to invent a station.

### Relationships that must not be created in v1

Do not create relationships from `dim_station`, `dim_vehicle_type`, or
`dim_region` directly to facts on their stable IDs. Those dimensions contain
multiple rows per ID at different timestamps. Such relationships would create
many-to-many filtering and duplicate or ambiguous totals.

Do not create a bidirectional relationship between facts. The station and
vehicle-type facts have different grains and would multiply rows.

Do not recreate `gold_station_availability_metrics` in Power BI or relate an
all-history station summary to `DimDate`; period summaries belong on the
timestamp-grain station fact.

### Target historical model prerequisite

For a future fully historical semantic model, Gold should expose explicit
relationship keys or foreign keys generated by the existing temporal join:

- `station_snapshot_key` on station facts
- `vehicle_type_snapshot_key` on vehicle-type and free-bike facts
- `region_snapshot_key` on station facts
- `pricing_plan_snapshot_key` on free-bike facts

Those keys should point to the exact matched snapshot dimension rows, not be
recomputed in DAX. Once present, the snapshot dimensions can replace the
identity helpers with active one-to-many relationships. This is a small Gold
contract enhancement, not a redesign of Raw/Silver/Gold, and is intentionally
not implemented by this design task.

## Date and time strategy

`dim_date` is the active date dimension. It contains only dates present in
station facts and relates through `date_key`. Mark it as the model's date
table using `calendar_date` when building the report.

When the Gold export and report are explicitly migrated, keep both timestamps
in every fact. Use canonical UTC `observed_at` to
distinguish snapshots, order observations, drive relationships, and implement
latest-snapshot measures. Use `observed_at_local` for local time-series axes,
tooltips, and local-time detail views.

Use each fact's existing `date_key` and `hour_of_day` values for local-date and
local-hour charts and slicers. They are derived from `observed_at_local`.
A separate time dimension is not useful yet: there are no time attributes beyond
hour in Gold, and adding one would add a relationship without adding meaning.
A small 0-23 helper table can be added later if a reusable sort/display label
is required; it should remain disconnected or relate separately to each fact,
not bridge facts together.

Power BI should not infer local time from the machine. The Gold generator
defines an explicit `Europe/Warsaw` conversion, including CET/CEST and
midnight crossings, but the current report continues to use UTC
`observed_at` until that Gold export is regenerated and the report model is
updated together. All snapshot identity, incremental processing, joins, and
latest-state logic remain on UTC `observed_at`.

## Slowly changing attributes

The implemented Gold dimensions preserve attributes by `entity ID +
observed_at`; this is a lightweight temporal snapshot strategy, not SCD Type 2.
Do not create surrogate SCD keys in Power BI for v1. Use the latest identity
helpers for stable operational labels, document their current-state meaning,
and defer historical attribute slicing until explicit Gold snapshot keys exist.

## Power BI import shaping

## Report pages

### 1. System Availability

Use `FactSystemAvailability` for current state cards and historical system
trends. Show latest `available_station_bikes`, `station_count`,
`empty_station_count`, `available_station_ebikes`,
`available_station_regular_bikes`, and `available_free_bikes` for
current state. Historical visuals use `observed_at` on the axis and explicitly
label averages, minimums, maximums, or snapshot counts when summarizing a
period. Do not expose capacity, docks, utilization, demand, rides, or revenue
measures.

### 2. Station Availability

Use `FactStationAvailability` for the latest station ranking, map/spatial
distribution, and station history. Current visuals resolve the maximum
`observed_at` in context. Historical visuals retain station plus
`observed_at` grain and can calculate average, minimum, maximum, and
empty-state summaries directly from the fact. These visuals identify
persistent or unusual observed availability patterns; they do not claim
demand or utilization.

### 3. Vehicle State

Use `FactStationVehicleTypeAvailability` for vehicle-type composition and
history, and `FactFreeBikeSnapshot` for visible-bike state and location.
Current visuals resolve one selected/latest timestamp. Historical composition
keeps `observed_at` visible. Free-bike cards and maps must say visible or
observed bikes because absence from the feed is not evidence of a trip or
utilization.

Across all pages, keep `observed_at` in tooltips and detail tables, use the
identity helpers for descriptive slicing, and avoid relationships between
facts. Power BI should consume Gold Parquet outputs directly; it should not
duplicate Raw-to-Silver or Silver-to-Gold transformations.

For each identity helper:

1. Load the corresponding Gold Parquet table.
2. Sort by stable ID and `observed_at` descending.
3. Keep the first row per stable ID.
4. Keep descriptive columns and the stable ID.
5. Do not remove `observed_at` from the hidden source query; retain it for
   auditability.

For facts, preserve nulls, numeric types, UTC timestamps, and the declared
Gold grain. Do not merge station-level measures into the vehicle-type fact or
free-bike fact.
