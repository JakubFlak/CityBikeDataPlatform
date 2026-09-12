"""Raw Parquet persistence for GBFS observations."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from bike_data.gbfs import GBFSFeed


class RawSnapshotStore:
    """Write one immutable Parquet file per feed observation."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write(
        self,
        feed_name: str,
        source_url: str,
        feed: "GBFSFeed",
        observed_at: datetime,
    ) -> Path:
        """Persist a complete source envelope without flattening its payload."""

        observed_at = observed_at.astimezone(UTC)
        timestamp = observed_at.strftime("%Y%m%dT%H%M%S.%fZ")
        path = self.root / feed_name / f"observed_at={timestamp}" / "snapshot.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.table(
            {
                "feed_name": [feed_name],
                "source_url": [source_url],
                "observed_at": [observed_at.isoformat()],
                "last_updated": [feed.last_updated],
                "ttl": [feed.ttl],
                "version": [feed.version],
                "data_json": [
                    json.dumps(feed.data, ensure_ascii=True, separators=(",", ":"))
                ],
                "source_payload_json": [
                    json.dumps(feed.payload, ensure_ascii=True, separators=(",", ":"))
                ],
            }
        )
        pq.write_table(table, path)
        return path
