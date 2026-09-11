import unittest

from url_sms_plugin.config.settings import load_settings
from url_sms_plugin.config.validator import ConfigurationError, validate_settings


def valid_config() -> dict:
    return {
        "urls": [{"url": "https://example.com"}],
        "l1Recipients": [{"number": "1111111111"}],
        "l2Recipients": [{"number": "2222222222"}],
        "l3Recipients": [{"number": "3333333333"}],
        "l2AfterMinutes": 30,
        "l3AfterMinutes": 60,
        "pollingInterval": 60,
        "maxRedirects": 5,
        "cacheRetentionMinutes": 1440,
        "smsApiUrl": "https://sms.example.test/send",
        "smsApiUsername": "example-user",
        "smsApiPassword": "example-password",
        "smsApiCookieId": "example-cookie",
        "dryRun": True,
    }


class SettingsTests(unittest.TestCase):
    def test_loads_nested_local_activation(self) -> None:
        settings = load_settings({"pythonLocal": valid_config()})

        validate_settings(settings)

        self.assertEqual(settings.urls[0].url, "https://example.com")
        self.assertEqual(settings.escalation.l2_after_minutes, 30)
        self.assertEqual(settings.sms_api.cookie_id, "example-cookie")

    def test_rejects_out_of_order_criticality_delays(self) -> None:
        config = valid_config()
        config["l3AfterMinutes"] = 30

        with self.assertRaisesRegex(ConfigurationError, "L3 criticality delay"):
            validate_settings(load_settings(config))

    def test_rejects_duplicate_urls(self) -> None:
        config = valid_config()
        config["urls"].append({"url": "https://example.com"})

        with self.assertRaisesRegex(ConfigurationError, "unique"):
            validate_settings(load_settings(config))

    def test_rejects_missing_sms_cookie(self) -> None:
        config = valid_config()
        config["smsApiCookieId"] = ""

        with self.assertRaisesRegex(ConfigurationError, "JSESSIONID"):
            validate_settings(load_settings(config))
