"""Publish URL availability results as Dynatrace metrics."""

from __future__ import annotations

from socket import gethostname
from typing import Protocol

from url_sms_plugin.models.url_check import UrlCheckResult

URL_STATUS_METRIC = "custom.url.availability.status"


class MetricReporter(Protocol):
    """The subset of the Dynatrace extension API used by this publisher."""

    def report_metric(self, key: str, value: int, dimensions: dict[str, str]) -> None:
        """Send a gauge metric to Dynatrace."""


class MetricsPublisher:
    """Report normalized URL statuses using stable host and URL dimensions."""

    def __init__(self, extension: MetricReporter, host: str | None = None) -> None:
        self._extension = extension
        self._host = host or gethostname()

    def url_status(self, result: UrlCheckResult) -> None:
        """Publish exactly one status metric for one final URL check result."""
        self._extension.report_metric(
            URL_STATUS_METRIC,
            result.status_code,
            dimensions={"Host": self._host, "URL": result.url},
        )
