"""Dispatch alert actions to configured SMS recipients."""

from url_sms_plugin.clients.sms_client import SmsClient
from url_sms_plugin.models.alerting import AlertAction, EscalationLevel
from url_sms_plugin.models.settings import EscalationSettings
from url_sms_plugin.processing.sms_formatter import format_sms


class NotificationService:
    def __init__(self, client: SmsClient, escalation: EscalationSettings) -> None:
        self._client = client
        self._escalation = escalation

    def dispatch(self, action: AlertAction) -> bool:
        """Send an action to all selected recipients; success requires all sends."""
        payload = format_sms(action)
        return all(self._client.send(payload, recipient) for recipient in self._recipients(action))

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
