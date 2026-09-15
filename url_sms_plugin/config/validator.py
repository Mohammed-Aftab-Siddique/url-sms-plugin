"""Validation rules for URL SMS Plugin settings."""

from url_sms_plugin.models.settings import ExtensionSettings


class ConfigurationError(ValueError):
    """Raised when the activation configuration is invalid."""


def _validate_urls(settings: ExtensionSettings) -> None:
    if not settings.urls:
        raise ConfigurationError("Configure at least one URL.")

    urls = [target.url for target in settings.urls]
    if any(not url for url in urls):
        raise ConfigurationError("URL values cannot be empty.")

    if len(set(urls)) != len(urls):
        raise ConfigurationError("URL values must be unique.")


def _validate_application_name(settings: ExtensionSettings) -> None:
    if not settings.application_name:
        raise ConfigurationError("Application name cannot be empty.")


def _validate_recipients(settings: ExtensionSettings) -> None:
    levels = {
        "L1": settings.escalation.l1,
        "L2": settings.escalation.l2,
        "L3": settings.escalation.l3,
    }

    for name, level in levels.items():
        if not level.recipients:
            raise ConfigurationError(f"{name} must contain at least one recipient.")

        if any(not recipient for recipient in level.recipients):
            raise ConfigurationError(f"{name} recipient values cannot be empty.")


def _validate_timing(settings: ExtensionSettings) -> None:
    if settings.escalation.l2_after_minutes <= 0:
        raise ConfigurationError("L2 criticality delay must be greater than zero.")

    if settings.escalation.l3_after_minutes <= settings.escalation.l2_after_minutes:
        raise ConfigurationError("L3 criticality delay must be greater than the L2 criticality delay.")

    if settings.polling_interval < 60:
        raise ConfigurationError("Polling interval must be at least 60 seconds.")

    if settings.max_redirects < 0:
        raise ConfigurationError("Maximum redirects cannot be negative.")

    if settings.cache_retention_minutes <= 0:
        raise ConfigurationError("Cache retention must be greater than zero.")


def _validate_sms_api(settings: ExtensionSettings) -> None:
    if not settings.sms_api.url:
        raise ConfigurationError("SMS API URL cannot be empty.")

    if not settings.sms_api.username:
        raise ConfigurationError("SMS API username cannot be empty.")

    if not settings.sms_api.password:
        raise ConfigurationError("SMS API password cannot be empty.")

    if not settings.sms_api.cookie_id:
        raise ConfigurationError("SMS API JSESSIONID cannot be empty.")


def validate_settings(settings: ExtensionSettings) -> None:
    """Validate the cross-field rules not expressible in the activation schema."""
    _validate_application_name(settings)
    _validate_urls(settings)
    _validate_recipients(settings)
    _validate_timing(settings)
    _validate_sms_api(settings)
