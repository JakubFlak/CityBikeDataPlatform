"""Discovery, validation, and raw ingestion for the required GBFS feeds."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bike_data.gbfs_client import GBFSHTTPClient
from bike_data.storage import RawSnapshotStore

DISCOVERY_URL = "https://gbfs.nextbike.net/maps/gbfs/v2/nextbike_pl/gbfs.json"
REQUIRED_FEEDS = (
    "vehicle_types",
    "station_information",
    "station_status",
    "free_bike_status",
    "system_regions",
    "system_pricing_plans",
)


class GBFSContractError(ValueError):
    """Raised when a provider response does not match the GBFS contract."""


@dataclass(frozen=True)
class FeedDefinition:
    """A feed name and URL discovered from the provider."""

    name: str
    url: str


@dataclass(frozen=True)
class GBFSFeed:
    """Validated source envelope, retaining the complete original payload."""

    last_updated: int
    ttl: int
    version: str
    data: dict[str, Any]
    payload: dict[str, Any]


def discover_feeds(
    client: GBFSHTTPClient, discovery_url: str = DISCOVERY_URL
) -> dict[str, FeedDefinition]:
    """Discover exactly the required feeds from the Polish language section."""

    document = client.get_json(discovery_url)
    try:
        feeds = document["data"]["pl"]["feeds"]
    except (KeyError, TypeError) as error:
        raise GBFSContractError(
            "Discovery response has no data.pl.feeds section"
        ) from error

    if not isinstance(feeds, list):
        raise GBFSContractError("Discovery data.pl.feeds must be a list")

    discovered: dict[str, FeedDefinition] = {}
    for feed in feeds:
        if not isinstance(feed, Mapping):
            continue
        name = feed.get("name")
        url = feed.get("url")
        if isinstance(name, str) and isinstance(url, str) and name in REQUIRED_FEEDS:
            discovered[name] = FeedDefinition(name=name, url=url)

    missing = [name for name in REQUIRED_FEEDS if name not in discovered]
    if missing:
        raise GBFSContractError(
            f"Discovery is missing required feeds: {', '.join(missing)}"
        )
    return discovered


def validate_gbfs_envelope(payload: Mapping[str, Any]) -> GBFSFeed:
    """Validate and return the common GBFS response envelope."""

    required = ("last_updated", "ttl", "version", "data")
    missing = [field for field in required if field not in payload]
    if missing:
        raise GBFSContractError(
            f"GBFS response is missing fields: {', '.join(missing)}"
        )

    last_updated = payload["last_updated"]
    ttl = payload["ttl"]
    version = payload["version"]
    data = payload["data"]
    if isinstance(last_updated, bool) or not isinstance(last_updated, int):
        raise GBFSContractError("GBFS last_updated must be an integer")
    if isinstance(ttl, bool) or not isinstance(ttl, int):
        raise GBFSContractError("GBFS ttl must be an integer")
    if not isinstance(version, str):
        raise GBFSContractError("GBFS version must be a string")
    if not isinstance(data, dict):
        raise GBFSContractError("GBFS data must be an object")

    return GBFSFeed(
        last_updated=last_updated,
        ttl=ttl,
        version=version,
        data=data,
        payload=dict(payload),
    )


class GBFSIngestor:
    """Discover and persist the six required feeds."""

    def __init__(
        self,
        client: GBFSHTTPClient,
        store: RawSnapshotStore,
        discovery_url: str = DISCOVERY_URL,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.client = client
        self.store = store
        self.discovery_url = discovery_url
        self.clock = clock or (lambda: datetime.now(UTC))

    def ingest_all(self) -> list:
        """Retrieve and persist all required feeds in deterministic feed order."""

        definitions = discover_feeds(self.client, self.discovery_url)
        snapshots = []
        for feed_name in REQUIRED_FEEDS:
            definition = definitions[feed_name]
            payload = self.client.get_json(definition.url)
            feed = validate_gbfs_envelope(payload)
            observed_at = self.clock()
            if observed_at.tzinfo is None or observed_at.utcoffset() is None:
                raise ValueError("clock must return a timezone-aware datetime")
            snapshots.append(
                self.store.write(
                    feed_name=feed_name,
                    source_url=definition.url,
                    feed=feed,
                    observed_at=observed_at.astimezone(UTC),
                )
            )
        return snapshots
