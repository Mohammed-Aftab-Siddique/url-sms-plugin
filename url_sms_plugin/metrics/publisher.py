"""Publish URL availability results as Dynatrace metrics."""

from __future__ import annotations

from socket import AF_INET, SOCK_DGRAM, gethostbyname_ex, gethostname, socket
from typing import Protocol

from url_sms_plugin.models.url_check import UrlCheckResult

URL_STATUS_METRIC = "custom.url.availability.status"


class MetricReporter(Protocol):
    """The subset of the Dynatrace extension API used by this publisher."""

    def report_metric(self, key: str, value: int, dimensions: dict[str, str]) -> None:
        """Send a gauge metric to Dynatrace."""


class MetricsPublisher:
    """Report normalized URL statuses using stable host-IP and URL dimensions."""

    def __init__(self, extension: MetricReporter, host_ip: str | None = None) -> None:
        self._extension = extension
        self._host_ip = host_ip or self._resolve_host_ip()

    def url_status(self, result: UrlCheckResult) -> None:
        """Publish exactly one status metric for one final URL check result."""
        self._extension.report_metric(
            URL_STATUS_METRIC,
            result.status_code,
            dimensions={"Host": self._host_ip, "URL": result.url},
        )

    @staticmethod
    def _resolve_host_ip() -> str:
        """Return the active IPv4 interface address without sending traffic."""
        try:
            with socket(AF_INET, SOCK_DGRAM) as probe:
                probe.connect(("192.0.2.1", 80))
                address = probe.getsockname()[0]
                if not address.startswith("127."):
                    return address
        except OSError:
            pass
        try:
            addresses = gethostbyname_ex(gethostname())[2]
            return next(
                (address for address in addresses if not address.startswith("127.")),
                "127.0.0.1",
            )
        except OSError:
            return "127.0.0.1"
