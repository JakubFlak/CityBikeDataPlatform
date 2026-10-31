# GBFS Ingestion

## Discovery and required feeds

The client requests the configured Nextbike discovery document:

`https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/gbfs.json`

It discovers feed URLs in `data.pl.feeds`; it does not construct them from
filenames. The required feeds are `vehicle_types`, `station_information`,
`station_status`, `free_bike_status`, `system_regions`, and
`system_pricing_plans`. Discovery fails if a required feed is missing.

## HTTP behavior and validation

The default request timeout is 30 seconds. The client makes at most three
attempts for transient transport errors and HTTP 429/5xx responses, with
configured retry waits of 10 and 30 seconds. Non-retryable HTTP errors,
invalid JSON, invalid feed envelopes, and exhausted retries are raised
explicitly.

Each feed response must contain `last_updated` (integer), `ttl` (integer),
`version` (string), and `data` (object). Additional envelope fields are
retained. Provider `last_updated` is distinct from application-generated,
timezone-aware UTC `observed_at`.

## Raw output

The complete pipeline invokes the ingestor through:

```powershell
uv run python scripts/run_pipeline.py
```

The standalone live smoke command writes Raw observations only:

```powershell
uv run python scripts/gbfs_live_smoke.py
```

Each feed observation is persisted at:

```text
data/raw/<feed_name>/observed_at=<UTC timestamp>/snapshot.parquet
```

Each Parquet file has one row for one feed observation and stores feed
identity, source URL, observation timestamp, envelope metadata, canonical
`data_json`, and the complete `source_payload_json`. Runtime data is excluded
from Git.

## Raw quality

Inspect the existing Raw directory with:

```powershell
uv run python scripts/inspect_raw_quality.py
```

The checks cover the physical schema and one-row grain, required metadata,
timestamp compatibility, JSON validity, expected collections and
feed-specific identifiers, payload equivalence, and metadata consistency.
The coordinator validates Raw after ingestion and stops on fatal quality
errors. Inspect the reported file before attempting repair; malformed records
are not silently discarded.

The ingestion layer does not filter to Wrocław subsets, infer trips, or build
analytical tables. Those concerns belong in later, explicitly documented
transformations.
