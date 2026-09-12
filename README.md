# City Bike Data Platform

This project is a local data platform for collecting and analysing Wroclaw
bike-sharing data. The current phase provides a GBFS discovery and raw
ingestion layer. See [GBFS ingestion](docs/GBFS_INGESTION.md) for its contract.

The complete local pipeline is available as one command:

```text
python scripts/run_pipeline.py
```

It runs GBFS ingestion, Raw quality checks, incremental Silver, and
incremental Gold processing. See [lightweight orchestration](docs/ORCHESTRATION.md)
for scheduling, retries, configuration, and GitHub Actions artifacts.

## Development

The project uses `uv` for dependency management:

```text
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Runtime settings are read from environment variables and default to local
development values:

- `BIKE_DATA_ENV`
- `BIKE_DATA_LOG_LEVEL`
- `BIKE_DATA_RAW_DIR`
- `BIKE_DATA_SILVER_DIR`
- `BIKE_DATA_GOLD_DIR`
- `BIKE_DATA_GBFS_DISCOVERY_URL`
- `BIKE_DATA_HTTP_TIMEOUT`
