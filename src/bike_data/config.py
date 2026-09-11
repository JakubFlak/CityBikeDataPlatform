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


def load_settings() -> Settings:
    """Load settings from environment variables, using local defaults."""

    return Settings(
        environment=os.getenv("BIKE_DATA_ENV", "development"),
        log_level=os.getenv("BIKE_DATA_LOG_LEVEL", "INFO").upper(),
        raw_data_dir=Path(os.getenv("BIKE_DATA_RAW_DIR", "data/raw")),
    )
