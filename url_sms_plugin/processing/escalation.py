"""Time-based URL alert escalation helpers."""

from datetime import datetime

from url_sms_plugin.models.alerting import EscalationLevel
from url_sms_plugin.models.settings import EscalationSettings


def current_level(
    first_failed_at: datetime,
    now: datetime,
    settings: EscalationSettings,
) -> EscalationLevel:
    """Return the highest criticality threshold reached by a continuous failure."""
    elapsed_minutes = (now - first_failed_at).total_seconds() / 60
    if elapsed_minutes >= settings.l3_after_minutes:
        return EscalationLevel.L3
    if elapsed_minutes >= settings.l2_after_minutes:
        return EscalationLevel.L2
    return EscalationLevel.L1


def levels_through(level: EscalationLevel) -> tuple[EscalationLevel, ...]:
    """Return every recipient level that should receive a recovery message."""
    if level == EscalationLevel.L3:
        return (EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3)
    if level == EscalationLevel.L2:
        return (EscalationLevel.L1, EscalationLevel.L2)
    return (EscalationLevel.L1,)
