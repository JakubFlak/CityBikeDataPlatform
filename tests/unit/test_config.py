from pathlib import Path

from bike_data.config import load_settings


def test_load_settings_uses_local_defaults(monkeypatch):
    monkeypatch.delenv("BIKE_DATA_ENV", raising=False)
    monkeypatch.delenv("BIKE_DATA_LOG_LEVEL", raising=False)
    monkeypatch.delenv("BIKE_DATA_RAW_DIR", raising=False)
    monkeypatch.delenv("BIKE_DATA_SILVER_DIR", raising=False)
    monkeypatch.delenv("BIKE_DATA_GOLD_DIR", raising=False)
    monkeypatch.delenv("BIKE_DATA_GBFS_DISCOVERY_URL", raising=False)
    monkeypatch.delenv("BIKE_DATA_HTTP_TIMEOUT", raising=False)

    settings = load_settings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.raw_data_dir == Path("data/raw")
    assert settings.silver_data_dir == Path("data/silver")
    assert settings.gold_data_dir == Path("data/gold")
    assert settings.http_timeout == 30


def test_load_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("BIKE_DATA_ENV", "test")
    monkeypatch.setenv("BIKE_DATA_LOG_LEVEL", "debug")
    monkeypatch.setenv("BIKE_DATA_RAW_DIR", "tmp/raw")
    monkeypatch.setenv("BIKE_DATA_SILVER_DIR", "tmp/silver")
    monkeypatch.setenv("BIKE_DATA_GOLD_DIR", "tmp/gold")
    monkeypatch.setenv("BIKE_DATA_GBFS_DISCOVERY_URL", "https://example.test/gbfs.json")
    monkeypatch.setenv("BIKE_DATA_HTTP_TIMEOUT", "12")

    settings = load_settings()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.raw_data_dir == Path("tmp/raw")
    assert settings.silver_data_dir == Path("tmp/silver")
    assert settings.gold_data_dir == Path("tmp/gold")
    assert settings.gbfs_discovery_url == "https://example.test/gbfs.json"
    assert settings.http_timeout == 12
