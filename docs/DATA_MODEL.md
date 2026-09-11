# Data Model

## General Principles

The analytical model follows a dimensional model with:

- dimensions describing relatively stable entities
- fact tables containing observations or events
- explicit table grain
- explicit primary/business keys
- timestamps for time-dependent observations

The model must distinguish between:

1. entity metadata
2. periodic system snapshots
3. completed trips/events

A snapshot is not a trip.

---

# Dimensions

## dim_station

### Purpose

Contains metadata describing bike-sharing stations.

### Grain

One record per station.

### Key

`station_id`

### Attributes

- `station_id`
- `name`
- `short_name`
- `latitude`
- `longitude`
- `region_id`
- `capacity`
- `is_virtual_station`

### Source

Nextbike `station_information`.

### Notes

This table describes station identity and metadata.

Availability information does not belong here because station availability changes over time.

Examples of changing values that belong in `fact_station_snapshot`:

- number of available bikes
- number of available docks
- renting status
- returning status

---

## dim_vehicle_type

### Purpose

Contains metadata describing vehicle types available in the system.

### Grain

One record per vehicle type.

### Key

`vehicle_type_id`

### Attributes

- `vehicle_type_id`
- `name`
- `form_factor`
- `propulsion_type`
- `rider_capacity`
- `max_range_meters`

### Source

Nextbike `vehicle_types`.

### Notes

Vehicle type metadata describes the characteristics of a vehicle category, not an individual bike.

---

## dim_pricing_plan

### Purpose

Contains pricing plan metadata used by the bike-sharing system.

### Grain

One record per pricing plan.

### Key

`pricing_plan_id`

### Attributes

The exact attributes depend on the structure of the Nextbike pricing feed.

At minimum, the model should preserve:

- `pricing_plan_id`
- currency
- pricing information

If a pricing plan contains multiple pricing intervals or conditions, these should be modelled separately rather than forcing a complex nested structure into a single row.

### Source

Nextbike `system_pricing_plans`.

---

# Facts

## fact_station_snapshot

### Purpose

Stores historical observations of station availability.

### Grain

One record per station per observation timestamp.

### Business Key

`station_id + observation_timestamp`

### Foreign Keys

- `station_id`

### Measures

- `num_bikes_available`
- `num_docks_available`

### Attributes

- `station_id`
- `observation_timestamp`
- `is_installed`
- `is_renting`
- `is_returning`

### Source

Nextbike `station_status`.

### Semantics

Each row represents the state of a station observed at a specific point in time.

For example:

```text
10:00 → Station A → 5 bikes → 10 docks
10:01 → Station A → 4 bikes → 11 docks
10:02 → Station A → 4 bikes → 11 docks
```

These are three observations of the same station, not three separate trips.

### Important

The observation timestamp represents when the platform collected/observed the state.

The source may also provide a `last_reported` timestamp. If retained, it should be clearly distinguished from the platform observation timestamp.

---

## fact_bike_snapshot

### Purpose

Stores historical observations of individual bikes.

### Grain

One record per bike per observation timestamp.

### Business Key

`bike_id + observation_timestamp`

### Foreign Keys

- `station_id`
- `vehicle_type_id`
- `pricing_plan_id`

### Attributes

- `bike_id`
- `station_id`
- `vehicle_type_id`
- `pricing_plan_id`
- `latitude`
- `longitude`
- `is_reserved`
- `is_disabled`
- `observation_timestamp`

### Source

Nextbike `free_bike_status`.

### Semantics

Each row represents the state/location of a bike observed at a specific point in time.

A bike may disappear from `free_bike_status` when it is no longer available in the public system, for example because it may be in use.

Therefore:

**absence of a bike from a snapshot does not by itself prove that a trip started.**

Similarly, observing a bike at another station later does not provide authoritative trip information.

---

## fact_trip

### Purpose

Contains completed bike rental trips.

### Grain

One record per completed rental.

### Status

Pending authoritative Wrocław Open Data trip history.

### Expected Key

The source UID of the rental, if provided by the authoritative source.

### Expected Attributes

- `trip_id`
- `bike_id`
- `start_time`
- `end_time`
- `start_station_id`
- `end_station_id`
- `duration_minutes`

### Expected Source

Wrocław Open Data — historical Wrocław Bike Sharing trips.

### Important

`fact_trip` should contain authoritative trip records when the official historical source is available.

Trip records must not be fabricated from GBFS snapshots.

If trip reconstruction from snapshots is implemented later, it must be modelled separately and explicitly identified as inferred data.

---

# Possible Derived Models

The following models may be introduced later if they provide clear analytical value.

## fact_station_daily

### Purpose

Daily station-level aggregates derived from `fact_station_snapshot`.

Possible metrics:

- average available bikes
- minimum available bikes
- maximum available bikes
- percentage of observations with zero bikes
- percentage of observations with zero docks
- station availability/utilisation indicators

### Grain

One record per station per calendar day.

This is a derived analytical model, not a raw source table.

---

# Relationships

Conceptually:

```text
dim_station
    │
    ├────────────── fact_station_snapshot
    │
    ├────────────── fact_bike_snapshot
    │
    └────────────── fact_trip

dim_vehicle_type
    │
    └────────────── fact_bike_snapshot

dim_pricing_plan
    │
    └────────────── fact_bike_snapshot
```

A future date dimension may be introduced if required by the BI model.

# Data Modelling Rules

- Every fact table must have an explicitly documented grain.
- Dimensions should describe entities rather than changing observations.
- Time-varying values belong in fact/snapshot tables.
- Raw API structures should not be copied blindly into the analytical model.
- Nested API structures should be normalized when required for analytical use.
- Do not create dimensions or fact tables without a clear analytical purpose.
- Authoritative and inferred data must remain distinguishable.