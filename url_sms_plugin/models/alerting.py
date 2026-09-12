"""State and actions for URL availability notifications."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EscalationLevel(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class AlertKind(str, Enum):
    FAILURE = "failure"
    ESCALATION = "escalation"
    RECOVERY = "recovery"


@dataclass(frozen=True, slots=True)
class UrlAlertState:
    """Durable notification state for one configured URL."""

    url: str
    is_failing: bool
    first_failed_at: datetime | None
    last_seen_at: datetime
    highest_notified_level: EscalationLevel | None
    recovered_at: datetime | None = None
    recovery_notified: bool = False
    pending_action_key: str | None = None
    delivery_attempts: int = 0


@dataclass(frozen=True, slots=True)
class AlertAction:
    """An alert decision for later formatting and SMS delivery."""

    url: str
    status_code: int
    kind: AlertKind
    levels: tuple[EscalationLevel, ...]
