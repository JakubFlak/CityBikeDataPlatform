from pathlib import Path

from bike_data.config import load_settings


def test_load_settings_uses_local_defaults(monkeypatch):
    monkeypatch.delenv("BIKE_DATA_ENV", raising=False)
    monkeypatch.delenv("BIKE_DATA_LOG_LEVEL", raising=False)
    monkeypatch.delenv("BIKE_DATA_RAW_DIR", raising=False)

    settings = load_settings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.raw_data_dir == Path("data/raw")


def test_load_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("BIKE_DATA_ENV", "test")
    monkeypatch.setenv("BIKE_DATA_LOG_LEVEL", "debug")
    monkeypatch.setenv("BIKE_DATA_RAW_DIR", "tmp/raw")

    settings = load_settings()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.raw_data_dir == Path("tmp/raw")
