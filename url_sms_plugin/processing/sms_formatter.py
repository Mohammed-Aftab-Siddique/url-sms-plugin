"""Render approved SMS notification payloads."""

from datetime import datetime
from zoneinfo import ZoneInfo

from url_sms_plugin.models.alerting import AlertAction


def format_sms(
    application_name: str,
    action: AlertAction,
    now: datetime | None = None,
) -> str:
    timestamp = now or datetime.now(ZoneInfo("Asia/Kolkata"))
    levels = ", ".join(level.value for level in action.levels)
    return (
        f"Incident: {application_name} URL Monitoring [{levels}]\n"
        f"URL: {action.url}\n"
        f"Status: {action.status_code}\n"
        f"Time: {timestamp.isoformat()}\n"
        "DT"
    )
