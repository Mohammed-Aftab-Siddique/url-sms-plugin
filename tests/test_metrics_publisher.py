import unittest
from unittest.mock import patch

from url_sms_plugin.metrics.publisher import URL_STATUS_METRIC, MetricsPublisher
from url_sms_plugin.models.url_check import UrlCheckError, UrlCheckResult


class FakeExtension:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, dict[str, str]]] = []

    def report_metric(self, key: str, value: int, dimensions: dict[str, str]) -> None:
        self.calls.append((key, value, dimensions))


class MetricsPublisherTests(unittest.TestCase):
    @patch("url_sms_plugin.metrics.publisher.socket")
    def test_resolves_active_interface_ip(self, socket_factory) -> None:
        probe = socket_factory.return_value.__enter__.return_value
        probe.getsockname.return_value = ("192.0.2.10", 12345)

        publisher = MetricsPublisher(FakeExtension())

        self.assertEqual(publisher._host_ip, "192.0.2.10")
        probe.connect.assert_called_once_with(("192.0.2.1", 80))

    def test_publishes_http_status_with_host_and_url_dimensions(self) -> None:
        extension = FakeExtension()
        publisher = MetricsPublisher(extension, host_ip="192.0.2.10")

        publisher.url_status(
            UrlCheckResult(url="https://example.com", status_code=503, attempts=2)
        )

        self.assertEqual(
            extension.calls,
            [
                (
                    URL_STATUS_METRIC,
                    503,
                    {"Host": "192.0.2.10", "URL": "https://example.com"},
                )
            ],
        )

    def test_publishes_normalized_transport_status(self) -> None:
        extension = FakeExtension()
        publisher = MetricsPublisher(extension, host_ip="192.0.2.10")

        publisher.url_status(
            UrlCheckResult(
                url="https://example.com",
                status_code=UrlCheckError.TLS.status_code,
                attempts=5,
                error=UrlCheckError.TLS,
            )
        )

        self.assertEqual(extension.calls[0][1], -1)
