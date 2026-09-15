"""Load local activation configuration into typed settings."""

from collections.abc import Mapping
from typing import Any

from url_sms_plugin.config.validator import ConfigurationError
from url_sms_plugin.models.settings import (
    EscalationLevelSettings,
    EscalationSettings,
    ExtensionSettings,
    SmsApiSettings,
    UrlTarget,
)


def _local_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    local_config = config.get("pythonLocal", config)

    if not isinstance(local_config, Mapping):
        raise ConfigurationError("Local activation configuration must be an object.")

    return local_config


def _required(config: Mapping[str, Any], key: str) -> Any:
    try:
        return config[key]
    except KeyError as exc:
        raise ConfigurationError(f"Missing required activation setting: {key}.") from exc


def _objects(config: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = _required(config, key)

    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise ConfigurationError(f"Activation setting {key} must be a list of objects.")

    return value


def _text(value: Any, key: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"Activation setting {key} must be text.")

    return value.strip()


def _integer(config: Mapping[str, Any], key: str) -> int:
    value = _required(config, key)

    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"Activation setting {key} must be an integer.")

    return value


def _recipients(config: Mapping[str, Any], key: str) -> EscalationLevelSettings:
    return EscalationLevelSettings(
        recipients=[
            _text(_required(recipient, "number"), f"{key}.number")
            for recipient in _objects(config, key)
        ]
    )


def load_settings(config: Mapping[str, Any]) -> ExtensionSettings:
    """Load a local activation object or its nested ``pythonLocal`` object."""
    local_config = _local_config(config)
    urls = [
        UrlTarget(url=_text(_required(item, "url"), "urls.url"))
        for item in _objects(local_config, "urls")
    ]

    dry_run = _required(local_config, "dryRun")
    if not isinstance(dry_run, bool):
        raise ConfigurationError("Activation setting dryRun must be a boolean.")

    return ExtensionSettings(
        application_name=_text(
            _required(local_config, "applicationName"),
            "applicationName",
        ),
        urls=urls,
        escalation=EscalationSettings(
            l1=_recipients(local_config, "l1Recipients"),
            l2=_recipients(local_config, "l2Recipients"),
            l3=_recipients(local_config, "l3Recipients"),
            l2_after_minutes=_integer(local_config, "l2AfterMinutes"),
            l3_after_minutes=_integer(local_config, "l3AfterMinutes"),
        ),
        polling_interval=_integer(local_config, "pollingInterval"),
        max_redirects=_integer(local_config, "maxRedirects"),
        cache_retention_minutes=_integer(local_config, "cacheRetentionMinutes"),
        sms_api=SmsApiSettings(
            url=_text(_required(local_config, "smsApiUrl"), "smsApiUrl"),
            username=_text(_required(local_config, "smsApiUsername"), "smsApiUsername"),
            password=_text(_required(local_config, "smsApiPassword"), "smsApiPassword"),
            cookie_id=_text(_required(local_config, "smsApiCookieId"), "smsApiCookieId"),
        ),
        dry_run=dry_run,
    )
