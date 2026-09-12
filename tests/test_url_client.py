import unittest

import requests

from url_sms_plugin.clients.url_client import UrlAvailabilityClient
from url_sms_plugin.models.url_check import UrlCheckError


class FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class FakeSession:
    def __init__(self, outcomes: list[FakeResponse | Exception]) -> None:
        self._outcomes = iter(outcomes)
        self.calls: list[tuple[str, bool, float]] = []
        self.max_redirects = 30

    def get(self, url: str, *, allow_redirects: bool, timeout: float) -> FakeResponse:
        self.calls.append((url, allow_redirects, timeout))
        outcome = next(self._outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class UrlAvailabilityClientTests(unittest.TestCase):
    def test_returns_http_200_without_retry(self) -> None:
        session = FakeSession([FakeResponse(200)])
        client = UrlAvailabilityClient(session=session)

        result = client.check("https://example.com", max_redirects=3)

        self.assertTrue(result.is_available)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(session.calls), 1)

    def test_returns_any_2xx_without_retry(self) -> None:
        session = FakeSession([FakeResponse(204)])
        client = UrlAvailabilityClient(session=session)

        result = client.check("https://example.com", max_redirects=3)

        self.assertTrue(result.is_available)
        self.assertEqual(result.status_code, 204)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0][1], True)
        self.assertEqual(session.max_redirects, 30)

    def test_retries_non_200_until_url_recovers(self) -> None:
        session = FakeSession([FakeResponse(503), FakeResponse(200)])
        delays: list[float] = []
        client = UrlAvailabilityClient(session=session, sleeper=delays.append)

        result = client.check("https://example.com", max_redirects=2)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(delays, [1.0])

    def test_normalizes_tls_failure_after_all_attempts(self) -> None:
        session = FakeSession([requests.exceptions.SSLError("certificate") for _ in range(5)])
        client = UrlAvailabilityClient(session=session, sleeper=lambda _: None)

        result = client.check("https://example.com", max_redirects=5)

        self.assertEqual(result.status_code, -1)
        self.assertEqual(result.error, UrlCheckError.TLS)
        self.assertEqual(result.attempts, 5)
        self.assertEqual(len(session.calls), 5)

    def test_normalizes_redirect_failure(self) -> None:
        session = FakeSession([requests.exceptions.TooManyRedirects("redirect loop") for _ in range(5)])
        client = UrlAvailabilityClient(session=session, sleeper=lambda _: None)

        result = client.check("https://example.com", max_redirects=1)

        self.assertEqual(result.status_code, -4)
        self.assertEqual(result.error, UrlCheckError.REDIRECT)

    def test_stops_when_retry_window_is_exhausted(self) -> None:
        clock_values = iter([0.0, 31.0])
        session = FakeSession([FakeResponse(503)])
        client = UrlAvailabilityClient(session=session, clock=lambda: next(clock_values))

        result = client.check("https://example.com", max_redirects=5)

        self.assertEqual(result.status_code, -2)
        self.assertEqual(result.error, UrlCheckError.TIMEOUT)
        self.assertEqual(result.attempts, 0)
        self.assertEqual(session.calls, [])
