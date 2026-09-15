"""Dispatch alert actions to configured SMS recipients."""

from url_sms_plugin.clients.sms_client import SmsClient
from url_sms_plugin.models.alerting import AlertAction, EscalationLevel
from url_sms_plugin.models.settings import EscalationSettings
from url_sms_plugin.processing.sms_formatter import format_sms


class NotificationService:
    def __init__(
        self,
        client: SmsClient,
        escalation: EscalationSettings,
        application_name: str,
    ) -> None:
        self._client = client
        self._escalation = escalation
        self._application_name = application_name

    def recipients(self, action: AlertAction) -> list[str]:
        return self._recipients(action)

    def dispatch(self, action: AlertAction, recipients: list[str]) -> set[str]:
        """Send once to each recipient and return only confirmed deliveries."""
        payload = format_sms(self._application_name, action)
        return {recipient for recipient in recipients if self._client.send(payload, recipient)}

    def _recipients(self, action: AlertAction) -> list[str]:
        recipients: list[str] = []
        for level in action.levels:
            recipients.extend(self._recipients_for_level(level))
        return list(dict.fromkeys(recipients))

    def _recipients_for_level(self, level: EscalationLevel) -> list[str]:
        if level == EscalationLevel.L1:
            return self._escalation.l1.recipients
        if level == EscalationLevel.L2:
            return self._escalation.l2.recipients
        return self._escalation.l3.recipients
