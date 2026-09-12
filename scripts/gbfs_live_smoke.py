"""Retrieve and persist a real Nextbike GBFS snapshot."""

from bike_data.config import load_settings
from bike_data.gbfs import GBFSIngestor
from bike_data.gbfs_client import GBFSHTTPClient
from bike_data.logging import configure_logging
from bike_data.storage import RawSnapshotStore


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    paths = GBFSIngestor(
        client=GBFSHTTPClient(timeout=30),
        store=RawSnapshotStore(settings.raw_data_dir),
    ).ingest_all()
    print(f"Persisted {len(paths)} GBFS snapshots under {settings.raw_data_dir}")


if __name__ == "__main__":
    main()
