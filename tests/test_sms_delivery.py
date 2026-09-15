import json
import unittest
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import requests
from urllib3.util import Timeout

from url_sms_plugin.clients.sms_client import SmsClient
from url_sms_plugin.models.alerting import AlertAction, AlertKind, EscalationLevel
from url_sms_plugin.models.settings import EscalationLevelSettings, EscalationSettings, SmsApiSettings
from url_sms_plugin.processing.notification_service import NotificationService
from url_sms_plugin.processing.sms_formatter import format_sms


def sms_settings() -> SmsApiSettings:
    return SmsApiSettings(
        url="http://localhost:3000/sms",
        username="test-user",
        password="test-password",
        cookie_id="test-cookie",
    )


def action() -> AlertAction:
    return AlertAction(
        url="https://example.com/health",
        status_code=404,
        kind=AlertKind.FAILURE,
        levels=(EscalationLevel.L1,),
    )


class SmsClientTests(unittest.TestCase):
    @patch("url_sms_plugin.clients.sms_client.requests.post")
    def test_posts_expected_form_and_accepts_any_2xx_response(self, post: Mock) -> None:
        response = Mock()
        response.status_code = 204
        response.raise_for_status.return_value = None
        post.return_value = response

        delivered = SmsClient(sms_settings(), dry_run=False).send("message", "9999999999")

        self.assertTrue(delivered)
        _, kwargs = post.call_args
        self.assertEqual(kwargs["headers"]["Cookie"], "JSESSIONID=test-cookie")
        self.assertIsInstance(kwargs["timeout"], Timeout)
        self.assertEqual(kwargs["timeout"].connect_timeout, 5)
        self.assertEqual(kwargs["timeout"].total, 10)
        self.assertTrue(kwargs["stream"])
        self.assertEqual(
            json.loads(kwargs["data"]["auth"]),
            {"user": "test-user", "password": "test-password", "appName": "Ecamptest"},
        )
        self.assertEqual(
            json.loads(kwargs["data"]["jsonString"]),
            {"campaign": "AppDynamics", "dynParam": ["message", "", "", "9999999999"]},
        )

    @patch("url_sms_plugin.clients.sms_client.requests.post")
    def test_returns_false_when_gateway_request_fails(self, post: Mock) -> None:
        post.side_effect = requests.ConnectionError("unavailable")

        self.assertFalse(SmsClient(sms_settings(), dry_run=False).send("message", "9999999999"))


class NotificationServiceTests(unittest.TestCase):
    def test_returns_only_recipients_with_confirmed_delivery(self) -> None:
        client = Mock()
        client.send.side_effect = [True, False]
        escalation = EscalationSettings(
            l1=EscalationLevelSettings(["111", "222"]),
            l2=EscalationLevelSettings([]),
            l3=EscalationLevelSettings([]),
            l2_after_minutes=30,
            l3_after_minutes=60,
        )
        service = NotificationService(client, escalation, "Example Application")

        self.assertEqual(service.dispatch(action(), ["111", "222"]), {"111"})


class SmsFormatterTests(unittest.TestCase):
    def test_incident_uses_application_name_monitoring_text_and_escalation_level(self) -> None:
        message = format_sms(
            "Example Application",
            action(),
            datetime(2026, 9, 12, 18, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
        )

        self.assertIn("Incident: Example Application URL Monitoring [L1]", message)
        self.assertIn("Status: 404", message)
        self.assertNotIn("Not Found", message)
