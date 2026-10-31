# Data Model

This document describes the implemented Gold contract. Detailed source
columns and transformation rules are in [Silver](SILVER_MODEL.md) and
[Gold](GOLD_MODEL.md). All snapshot facts represent observed states, not
trips or transactions.

## Dimensions

| Table | Grain / key | Role |
| --- | --- | --- |
| `dim_date` | One row per local calendar date; `date_key` (`YYYYMMDD`). | Calendar attributes derived from dates present in Gold facts. |
| `dim_station` | Station + UTC `observed_at`. | Station attributes as observed in each station-information snapshot. |
| `dim_vehicle_type` | Vehicle type + UTC `observed_at`. | Vehicle metadata as observed in each vehicle-types snapshot; includes `is_ebike`. |
| `dim_region` | Region + UTC `observed_at`. | Region name as observed in each regions snapshot. |
| `dim_pricing_plan` | Plan + UTC `observed_at`. | Pricing plan attributes by source snapshot. |
| `dim_pricing_plan_tier` | Plan + tier index + UTC `observed_at`. | Nested pricing interval details. |

Entity dimensions retain repeated historical rows; they are snapshot
dimensions, not one-row-per-entity current dimensions and not SCD Type 2
surrogate-key dimensions. Power BI derives current-identity helpers for safe
entity slicers.

## Facts and aggregate

| Table | Grain / key | Main content |
| --- | --- | --- |
| `fact_station_availability` | One station state per `station_id + observed_at`. | Bike count, dock/capacity lineage, station status flags, region and local calendar fields. |
| `fact_station_vehicle_type_availability` | One station/vehicle count per `station_id + vehicle_type_id + observed_at`. | Nested vehicle availability count and e-bike flag; station measures are not repeated. |
| `fact_free_bike_snapshot` | One publicly listed bike per `bike_id + observed_at`. | Location and optional station, vehicle, pricing and state attributes. A visible-bike state is not a trip. |
| `gold_system_availability` | One system aggregate per station-status `observed_at`. | Station count, empty/available station counts, station bikes by type, and free bikes outside stations. |

Snapshot facts use canonical UTC `observed_at`. Gold also stores
`observed_at_local`, `date_key`, and `hour_of_day` derived in
`Europe/Warsaw` for presentation. They are not alternate snapshot keys.

## Source and matching rules

Raw and Silver preserve the six GBFS feeds. Silver natural keys include
`observed_at`; no snapshot is collapsed into a latest-only record.
Gold foreign-key alignment uses nearest observations within five minutes and
fails for missing, ambiguous, or out-of-tolerance matches. System bike totals
come from `station_status`; e-bike counts come from its normalized
`vehicle_types_available` child rows. The system aggregate's outside-station
free-bike count includes `free_bike_status` rows whose `station_id` is null,
matched to the nearest system observation.

`fact_trip` and authoritative Wrocław Open Data trip ingestion are not
implemented. GBFS absence or location changes must not be used to fabricate
trip records.

## Power BI relationships

`dim_date` filters each Gold fact by `date_key`. Power BI identity helper
tables filter station, region, and vehicle facts by stable IDs; they use the
latest available descriptive attribute and do not provide historically
versioned labels. `gold_system_availability` is already system-grain and has
no station or region relationship. See
[the semantic model](POWER_BI_MODEL.md) for the concrete imported tables and
relationship details.
