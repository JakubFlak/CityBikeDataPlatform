import logging

from bike_data.logging import configure_logging


def test_configure_logging_sets_requested_level(monkeypatch):
    basic_config_calls = []
    monkeypatch.setattr(
        logging,
        "basicConfig",
        lambda **kwargs: basic_config_calls.append(kwargs),
    )

    configure_logging("debug")

    assert basic_config_calls == [
        {
            "level": logging.DEBUG,
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
        }
    ]
