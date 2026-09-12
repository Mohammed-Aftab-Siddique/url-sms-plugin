"""HTTP availability checks with normalized, metric-safe outcomes."""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic, sleep

import requests

from url_sms_plugin.models.url_check import UrlCheckError, UrlCheckResult


class UrlAvailabilityClient:
    """Check a URL up to a fixed number of times within a total time window."""

    max_attempts = 5
    retry_window_seconds = 30

    def __init__(
        self,
        session: requests.Session | None = None,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self._session = session or requests.Session()
        self._clock = clock
        self._sleep = sleeper

    def check(self, url: str, max_redirects: int) -> UrlCheckResult:
        """Return the final HTTP result or a normalized transport failure.

        A check always has at most five attempts and never intentionally waits
        beyond the 30-second retry window. A response other than HTTP 200 is
        retried because it is eligible for an eventual availability alert.
        """
        deadline = self._clock() + self.retry_window_seconds
        original_max_redirects = getattr(self._session, "max_redirects", None)
        self._session.max_redirects = max_redirects

        try:
            for attempts in range(1, self.max_attempts + 1):
                remaining = deadline - self._clock()
                if remaining <= 0:
                    return UrlCheckResult(
                        url=url,
                        status_code=UrlCheckError.TIMEOUT.status_code,
                        attempts=attempts - 1,
                        error=UrlCheckError.TIMEOUT,
                    )

                result = self._request(url, attempts, remaining)
                if result.is_available or attempts == self.max_attempts:
                    return result

                remaining = deadline - self._clock()
                if remaining > 0:
                    self._sleep(min(1.0, remaining))
        finally:
            self._session.max_redirects = original_max_redirects

        raise RuntimeError("URL check finished without producing a result.")

    def _request(self, url: str, attempts: int, timeout: float) -> UrlCheckResult:
        try:
            response = self._session.get(url, allow_redirects=True, timeout=timeout)
            return UrlCheckResult(url=url, status_code=response.status_code, attempts=attempts)
        except requests.exceptions.SSLError:
            return self._failure(url, attempts, UrlCheckError.TLS)
        except requests.exceptions.TooManyRedirects:
            return self._failure(url, attempts, UrlCheckError.REDIRECT)
        except requests.exceptions.Timeout:
            return self._failure(url, attempts, UrlCheckError.TIMEOUT)
        except requests.exceptions.ConnectionError:
            return self._failure(url, attempts, UrlCheckError.CONNECTION)
        except requests.exceptions.RequestException:
            return self._failure(url, attempts, UrlCheckError.REQUEST)

    @staticmethod
    def _failure(url: str, attempts: int, error: UrlCheckError) -> UrlCheckResult:
        return UrlCheckResult(
            url=url,
            status_code=error.status_code,
            attempts=attempts,
            error=error,
        )
