"""Small HTTP client for retrieving JSON GBFS responses."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class GBFSHTTPError(RuntimeError):
    """Raised when a GBFS HTTP request cannot be completed or decoded."""


class GBFSHTTPClient:
    """Retrieve JSON documents with retries for transient failures."""

    def __init__(
        self,
        timeout: float = 30.0,
        max_attempts: int = 3,
        retry_delays: tuple[float, ...] = (10.0, 30.0),
    ) -> None:
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.retry_delays = retry_delays

    def get_json(self, url: str) -> dict:
        """Fetch ``url`` and return its JSON object."""
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "CityBikeDataPlatform/1.0",
            },
        )

        for attempt in range(1, self.max_attempts + 1):
            logger.info(
                "Fetching GBFS URL: %s (attempt %d/%d)",
                url,
                attempt,
                self.max_attempts,
            )

            try:
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read()

                document = json.loads(body)

                if not isinstance(document, dict):
                    raise GBFSHTTPError(
                        f"GBFS response must be a JSON object for {url}"
                    )

                return document

            except HTTPError as error:
                retryable = error.code == 429 or 500 <= error.code < 600

                if not retryable or attempt == self.max_attempts:
                    raise GBFSHTTPError(
                        f"GBFS request failed with HTTP {error.code} for {url}"
                    ) from error

                self._wait_before_retry(url, attempt)

            except (TimeoutError, URLError, OSError) as error:
                if attempt == self.max_attempts:
                    raise GBFSHTTPError(
                        f"GBFS request failed for {url}: {error}"
                    ) from error

                self._wait_before_retry(url, attempt)

            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise GBFSHTTPError(
                    f"GBFS response was not valid JSON for {url}"
                ) from error

        raise GBFSHTTPError(f"GBFS request failed for {url}")

    def _wait_before_retry(self, url: str, attempt: int) -> None:
        """Wait before retrying a transient request failure."""
        import time

        delay_index = min(attempt - 1, len(self.retry_delays) - 1)
        delay = self.retry_delays[delay_index]

        logger.warning(
            "Transient GBFS request failure for %s. Retrying in %.0f seconds...",
            url,
            delay,
        )

        time.sleep(delay)
