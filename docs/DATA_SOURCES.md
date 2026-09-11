# Data Sources

## 1. Nextbike GBFS

### Provider

Nextbike

### System

Wrocław Bike Sharing

### GBFS Version

GBFS 2.3

### Type

Real-time operational data.

### Update Frequency

The GBFS feeds are designed to provide frequently updated snapshots of the current system state.

The observed feeds currently indicate an update interval of approximately 60 seconds.

The ingestion process should not assume that the source is an event stream.

### Main Discovery Endpoint

`https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/gbfs.json`

The discovery feed should be used to identify the available GBFS feeds rather than hard-coding assumptions where possible.

---

## station_information

### Purpose

Provides relatively stable station metadata.

### Grain

One record per station.

### Important Fields

- `station_id`
- `name`
- `short_name`
- `lat`
- `lon`
- `region_id`
- `capacity`
- `is_virtual_station`
- `rental_uris`

### Used For

Primarily:

- `dim_station`

### Characteristics

This feed describes what stations exist and their metadata.

It does not describe historical station availability.

---

## station_status

### Purpose

Provides the current operational state of stations.

### Grain

One station per source observation.

### Important Fields

- `station_id`
- `num_bikes_available`
- `num_docks_available`
- `is_installed`
- `is_renting`
- `is_returning`
- `last_reported`

### Used For

Primarily:

- `fact_station_snapshot`

### Characteristics

This is snapshot data.

Repeated observations should be stored as historical snapshots rather than overwriting previous observations.

---

## free_bike_status

### Purpose

Provides the current state of individual publicly available bikes.

### Grain

One bike per source observation.

### Important Fields

- `bike_id`
- `station_id`
- `vehicle_type_id`
- `pricing_plan_id`
- `lat`
- `lon`
- `is_reserved`
- `is_disabled`
- `rental_uris`

### Used For

Primarily:

- `fact_bike_snapshot`

### Important Limitation

This is a snapshot of currently available bikes.

A bike disappearing from the feed does not provide authoritative evidence of a trip.

A later appearance at another station can provide evidence that a bike moved, but this should not automatically be interpreted as an authoritative trip.

---

## vehicle_types

### Purpose

Provides metadata describing vehicle types.

### Grain

One record per vehicle type.

### Important Fields

- `vehicle_type_id`
- `name`
- `form_factor`
- `propulsion_type`
- `rider_capacity`
- `max_range_meters`

### Used For

Primarily:

- `dim_vehicle_type`

---

## system_pricing_plans

### Purpose

Provides pricing plan information.

### Grain

One record per pricing plan, with potentially nested pricing intervals/conditions.

### Used For

Primarily:

- `dim_pricing_plan`

If required by the final model, nested pricing intervals should be normalized into a separate model.

---

# 2. Wrocław Open Data

## Przejazdy Wrocławskiego Roweru Miejskiego

### Provider

Urząd Miejski Wrocławia / Wydział Inżynierii Miejskiej

### Purpose

Historical trip data for Wrocław Bike Sharing.

### Expected Grain

One record per completed rental.

### Expected Fields

- rental UID
- bike number
- rental date
- return date
- rental station
- return station
- duration in minutes

### Intended Use

Authoritative source for:

- `fact_trip`

### Important

This source is preferred over reconstructing trips from GBFS snapshots.

The current public dataset availability/update status should be verified before building the historical trip ingestion.

At the time of project planning, the publicly exposed file was observed to contain stale data. The project should not assume that the source is currently up to date.

### Open Questions

- Is current historical data available through the public API?
- Is there an archive of historical files?
- Is there a stable endpoint suitable for automated ingestion?
- Is the current dataset affected by an update/harvesting issue?

These questions should be resolved before implementing authoritative trip ingestion.

---

# Source Classification

| Source | Type | Historical | Main Use |
|---|---|---:|---|
| Nextbike GBFS | Real-time snapshots | No | Operational state |
| Wrocław Open Data | Historical trips | Yes | `fact_trip` |

# General Source Rules

- Source schemas must not be silently changed.
- API failures must be visible in logs.
- Missing records must not be silently discarded.
- Source timestamps and ingestion timestamps should be distinguished.
- Raw responses/snapshots should be preserved before transformation.
- The project must clearly distinguish source facts from derived/inferred information.