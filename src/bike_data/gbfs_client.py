"""Small HTTP client for retrieving JSON GBFS responses."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class GBFSHTTPError(RuntimeError):
    """Raised when a GBFS HTTP request cannot be completed or decoded."""


class GBFSHTTPClient:
    """Retrieve JSON documents with an explicit timeout."""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def get_json(self, url: str) -> dict:
        """Fetch ``url`` and return its JSON object."""

        request = Request(url, headers={"Accept": "application/json"})
        logger.info("Fetching GBFS URL: %s", url)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as error:
            raise GBFSHTTPError(
                f"GBFS request failed with HTTP {error.code} for {url}"
            ) from error
        except (TimeoutError, URLError, OSError) as error:
            raise GBFSHTTPError(f"GBFS request failed for {url}: {error}") from error

        try:
            document = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise GBFSHTTPError(
                f"GBFS response was not valid JSON for {url}"
            ) from error

        if not isinstance(document, dict):
            raise GBFSHTTPError(f"GBFS response must be a JSON object for {url}")
        return document
