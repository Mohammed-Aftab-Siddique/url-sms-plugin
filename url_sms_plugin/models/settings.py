"""Typed activation settings for the URL SMS Plugin."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UrlTarget:
    url: str


@dataclass(frozen=True, slots=True)
class EscalationLevelSettings:
    recipients: list[str]


@dataclass(frozen=True, slots=True)
class EscalationSettings:
    l1: EscalationLevelSettings
    l2: EscalationLevelSettings
    l3: EscalationLevelSettings
    l2_after_minutes: int
    l3_after_minutes: int


@dataclass(frozen=True, slots=True)
class SmsApiSettings:
    url: str
    username: str
    password: str
    cookie_id: str


@dataclass(frozen=True, slots=True)
class ExtensionSettings:
    application_name: str
    urls: list[UrlTarget]
    escalation: EscalationSettings
    polling_interval: int
    max_redirects: int
    cache_retention_minutes: int
    sms_api: SmsApiSettings
    dry_run: bool
