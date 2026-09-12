"""Render approved SMS notification payloads."""

from datetime import datetime
from http import HTTPStatus
from zoneinfo import ZoneInfo

from url_sms_plugin.models.alerting import AlertAction
from url_sms_plugin.models.url_check import UrlCheckError


def format_sms(action: AlertAction, now: datetime | None = None) -> str:
    timestamp = now or datetime.now(ZoneInfo("Asia/Kolkata"))
    levels = ", ".join(level.value for level in action.levels)
    return (
        f"Incident: {_status_description(action.status_code)} [{levels}]\n"
        f"URL: {action.url}\n"
        f"Status: {action.status_code}\n"
        f"Time: {timestamp.isoformat()}\n"
        "DT"
    )


def _status_description(status_code: int) -> str:
    for error in UrlCheckError:
        if error.status_code == status_code:
            return error.label.replace("_", " ").title()
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return str(status_code)
