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

    @patch("url_sms_plugin.metrics.publisher.gethostbyname_ex", side_effect=OSError)
    @patch("url_sms_plugin.metrics.publisher.socket", side_effect=OSError)
    def test_uses_loopback_when_both_host_ip_lookups_fail(self, _socket_factory, _hostname_lookup) -> None:
        publisher = MetricsPublisher(FakeExtension())

        self.assertEqual(publisher._host_ip, "127.0.0.1")

    @patch("url_sms_plugin.metrics.publisher.gethostbyname_ex")
    @patch("url_sms_plugin.metrics.publisher.socket")
    def test_replaces_loopback_route_address_with_hostname_address(
        self,
        socket_factory,
        hostname_lookup,
    ) -> None:
        probe = socket_factory.return_value.__enter__.return_value
        probe.getsockname.return_value = ("127.0.0.1", 12345)
        hostname_lookup.return_value = ("host", [], ["192.0.2.20"])

        publisher = MetricsPublisher(FakeExtension())

        self.assertEqual(publisher._host_ip, "192.0.2.20")

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
                    {"host": "192.0.2.10", "url": "https://example.com"},
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
