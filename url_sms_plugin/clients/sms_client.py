"""Gateway-compatible SMS transport."""

import json

import requests
from urllib3.util import Timeout

from url_sms_plugin.models.settings import SmsApiSettings


class SmsClient:
    _connect_timeout_seconds = 5
    _total_timeout_seconds = 10

    def __init__(self, settings: SmsApiSettings, dry_run: bool) -> None:
        self._settings = settings
        self._dry_run = dry_run

    def send(self, payload: str, recipient: str) -> bool:
        if self._dry_run:
            return False
        try:
            return self._post(payload, recipient)
        except requests.RequestException:
            return False

    def _post(self, payload: str, recipient: str) -> bool:
        response = requests.post(
            self._settings.url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": f"JSESSIONID={self._settings.cookie_id}",
            },
            data={
                "auth": json.dumps(
                    {
                        "user": self._settings.username,
                        "password": self._settings.password,
                        "appName": "Ecamptest",
                    }
                ),
                "jsonString": json.dumps(
                    {"campaign": "AppDynamics", "dynParam": [payload, "", "", recipient]}
                ),
            },
            timeout=Timeout(
                connect=self._connect_timeout_seconds,
                read=self._connect_timeout_seconds,
                total=self._total_timeout_seconds,
            ),
            stream=True,
        )
        try:
            response.raise_for_status()
            return True
        finally:
            response.close()
