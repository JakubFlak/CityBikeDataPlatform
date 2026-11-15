"""Application settings loaded from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime settings needed by the project foundation."""

    environment: str = "development"
    log_level: str = "INFO"
    raw_data_dir: Path = Path("data/raw")
    silver_data_dir: Path = Path("data/silver")
    gold_data_dir: Path = Path("data/gold")
    gbfs_discovery_url: str = (
        "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/gbfs.json"
    )
    http_timeout: int = 30


def load_settings() -> Settings:
    """Load settings from environment variables, using local defaults."""

    return Settings(
        environment=os.getenv("BIKE_DATA_ENV", "development"),
        log_level=os.getenv("BIKE_DATA_LOG_LEVEL", "INFO").upper(),
        raw_data_dir=Path(os.getenv("BIKE_DATA_RAW_DIR", "data/raw")),
        silver_data_dir=Path(os.getenv("BIKE_DATA_SILVER_DIR", "data/silver")),
        gold_data_dir=Path(os.getenv("BIKE_DATA_GOLD_DIR", "data/gold")),
        gbfs_discovery_url=os.getenv(
            "BIKE_DATA_GBFS_DISCOVERY_URL",
            "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/gbfs.json",
        ),
        http_timeout=int(os.getenv("BIKE_DATA_HTTP_TIMEOUT", "30")),
    )
