"""Run one complete local GBFS data pipeline job."""

import logging

from bike_data.config import load_settings
from bike_data.logging import configure_logging
from bike_data.pipeline import run_pipeline


def main() -> int:
    settings = load_settings()
    configure_logging(settings.log_level)
    try:
        run_pipeline(settings)
    except Exception:
        logging.getLogger(__name__).exception("pipeline_failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
