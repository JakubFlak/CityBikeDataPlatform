import json
from datetime import UTC, datetime
from urllib.error import HTTPError

import pyarrow.parquet as pq
import pytest

from bike_data.gbfs import (
    DISCOVERY_URL,
    REQUIRED_FEEDS,
    FeedDefinition,
    GBFSContractError,
    GBFSIngestor,
    discover_feeds,
    validate_gbfs_envelope,
)
from bike_data.gbfs_client import GBFSHTTPClient, GBFSHTTPError
from bike_data.storage import RawSnapshotStore


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []

    def get_json(self, url):
        self.urls.append(url)
        return self.responses[url]


def discovery_document():
    return {
        "data": {
            "pl": {
                "feeds": [
                    {"name": name, "url": f"https://example.test/custom/{name}-feed"}
                    for name in REQUIRED_FEEDS
                ]
            }
        }
    }


def valid_feed():
    return {
        "last_updated": 1700000000,
        "ttl": 60,
        "version": "2.3",
        "data": {"nested": [{"station_id": "1", "capacity": 10}]},
        "provider_extension": {"kept": True},
    }


def test_discovery_selects_polish_required_feeds_and_uses_discovered_urls():
    client = FakeClient({DISCOVERY_URL: discovery_document()})

    feeds = discover_feeds(client)

    assert tuple(feeds) == REQUIRED_FEEDS
    assert feeds["station_status"] == FeedDefinition(
        "station_status", "https://example.test/custom/station_status-feed"
    )


def test_discovery_rejects_missing_required_feed():
    document = discovery_document()
    document["data"]["pl"]["feeds"].pop()

    with pytest.raises(GBFSContractError, match="system_pricing_plans"):
        discover_feeds(FakeClient({DISCOVERY_URL: document}))


@pytest.mark.parametrize("field", ["last_updated", "ttl", "version", "data"])
def test_validation_rejects_missing_envelope_field(field):
    payload = valid_feed()
    del payload[field]

    with pytest.raises(GBFSContractError, match=field):
        validate_gbfs_envelope(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("last_updated", "wrong"), ("ttl", "wrong"), ("version", 2.3), ("data", [])],
)
def test_validation_rejects_invalid_envelope_types(field, value):
    payload = valid_feed()
    payload[field] = value

    with pytest.raises(GBFSContractError, match=field):
        validate_gbfs_envelope(payload)


def test_validation_preserves_metadata_and_nested_payload():
    result = validate_gbfs_envelope(valid_feed())

    assert result.last_updated == 1700000000
    assert result.data["nested"][0]["capacity"] == 10
    assert result.payload["provider_extension"] == {"kept": True}


def test_ingestor_persists_all_feeds_with_separate_observation_timestamp(tmp_path):
    responses = {DISCOVERY_URL: discovery_document()}
    for name in REQUIRED_FEEDS:
        responses[f"https://example.test/custom/{name}-feed"] = valid_feed()
    client = FakeClient(responses)
    observed_at = datetime(2026, 9, 11, 12, 30, tzinfo=UTC)

    paths = GBFSIngestor(
        client,
        RawSnapshotStore(tmp_path),
        clock=lambda: observed_at,
    ).ingest_all()

    assert len(paths) == 6
    assert all(path.exists() for path in paths)
    table = pq.read_table(paths[2]).to_pylist()[0]
    assert table["feed_name"] == "station_status"
    assert table["last_updated"] == 1700000000
    assert table["observed_at"] == observed_at.isoformat()
    assert json.loads(table["data_json"])["nested"][0]["capacity"] == 10
    assert json.loads(table["source_payload_json"])["provider_extension"] == {
        "kept": True
    }


def test_raw_store_keeps_multiple_observations(tmp_path):
    store = RawSnapshotStore(tmp_path)
    feed = validate_gbfs_envelope(valid_feed())

    first = store.write(
        "station_status",
        "https://example.test/station-status",
        feed,
        datetime(2026, 9, 11, 12, 30, tzinfo=UTC),
    )
    second = store.write(
        "station_status",
        "https://example.test/station-status",
        feed,
        datetime(2026, 9, 11, 12, 31, tzinfo=UTC),
    )

    assert first != second
    assert first.exists()
    assert second.exists()


def test_http_client_handles_success(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"ok": true}'

    monkeypatch.setattr(
        "bike_data.gbfs_client.urlopen", lambda *args, **kwargs: Response()
    )

    assert GBFSHTTPClient(timeout=2).get_json("https://example.test") == {"ok": True}


def test_http_client_handles_malformed_json(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"not json"

    monkeypatch.setattr(
        "bike_data.gbfs_client.urlopen", lambda *args, **kwargs: Response()
    )

    with pytest.raises(GBFSHTTPError, match="not valid JSON"):
        GBFSHTTPClient().get_json("https://example.test")


def test_http_client_handles_request_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise TimeoutError("slow")

    monkeypatch.setattr("bike_data.gbfs_client.urlopen", fail)

    with pytest.raises(GBFSHTTPError, match="request failed"):
        GBFSHTTPClient().get_json("https://example.test")


def test_http_client_handles_http_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise HTTPError("https://example.test", 503, "unavailable", {}, None)

    monkeypatch.setattr("bike_data.gbfs_client.urlopen", fail)

    with pytest.raises(GBFSHTTPError, match="HTTP 503"):
        GBFSHTTPClient().get_json("https://example.test")
