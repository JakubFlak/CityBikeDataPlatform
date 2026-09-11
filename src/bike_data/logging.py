"""Logging setup for application modules."""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure concise console logging for the application."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
