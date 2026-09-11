"""Models for normalized URL availability results."""

from dataclasses import dataclass
from enum import Enum


class UrlCheckError(Enum):
    """Custom metric values for failures that have no HTTP status code."""

    TLS = ("tls", -1)
    TIMEOUT = ("timeout", -2)
    CONNECTION = ("connection", -3)
    REDIRECT = ("redirect", -4)
    REQUEST = ("request", -5)

    def __init__(self, label: str, status_code: int) -> None:
        self.label = label
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class UrlCheckResult:
    """One final result from checking a configured URL."""

    url: str
    status_code: int
    attempts: int
    error: UrlCheckError | None = None

    @property
    def is_available(self) -> bool:
        return self.status_code == 200
