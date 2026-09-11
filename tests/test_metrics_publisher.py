import unittest

from url_sms_plugin.metrics.publisher import URL_STATUS_METRIC, MetricsPublisher
from url_sms_plugin.models.url_check import UrlCheckError, UrlCheckResult


class FakeExtension:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, dict[str, str]]] = []

    def report_metric(self, key: str, value: int, dimensions: dict[str, str]) -> None:
        self.calls.append((key, value, dimensions))


class MetricsPublisherTests(unittest.TestCase):
    def test_publishes_http_status_with_host_and_url_dimensions(self) -> None:
        extension = FakeExtension()
        publisher = MetricsPublisher(extension, host="oneagent-host")

        publisher.url_status(
            UrlCheckResult(url="https://example.com", status_code=503, attempts=2)
        )

        self.assertEqual(
            extension.calls,
            [
                (
                    URL_STATUS_METRIC,
                    503,
                    {"Host": "oneagent-host", "URL": "https://example.com"},
                )
            ],
        )

    def test_publishes_normalized_transport_status(self) -> None:
        extension = FakeExtension()
        publisher = MetricsPublisher(extension, host="oneagent-host")

        publisher.url_status(
            UrlCheckResult(
                url="https://example.com",
                status_code=UrlCheckError.TLS.status_code,
                attempts=5,
                error=UrlCheckError.TLS,
            )
        )

        self.assertEqual(extension.calls[0][1], -1)
