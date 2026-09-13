import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from url_sms_plugin.cache.cache_manager import CacheError, CacheManager
from url_sms_plugin.models.alerting import AlertKind, EscalationLevel
from url_sms_plugin.models.settings import EscalationLevelSettings, EscalationSettings
from url_sms_plugin.models.url_check import UrlCheckResult
from url_sms_plugin.processing.alert_engine import AlertEngine


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value

    def advance(self, minutes: int) -> None:
        self.value += timedelta(minutes=minutes)


def escalation_settings() -> EscalationSettings:
    return EscalationSettings(
        l1=EscalationLevelSettings(["111"]),
        l2=EscalationLevelSettings(["222"]),
        l3=EscalationLevelSettings(["333"]),
        l2_after_minutes=30,
        l3_after_minutes=60,
    )


class AlertEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.clock = Clock(datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Kolkata")))
        self.cache = CacheManager(Path(self.temporary_directory.name), "test-activation")
        self.engine = AlertEngine(self.cache, escalation_settings(), 60, now=self.clock.now)
        self.failure = UrlCheckResult("https://example.com", 503, 1)
        self.success = UrlCheckResult("https://example.com", 200, 1)

    def test_failure_escalation_and_recovery_are_emitted_once_each(self) -> None:
        action = self.engine.process(self.failure)
        self.assertEqual(action.kind, AlertKind.FAILURE)
        self.assertEqual(action.levels, (EscalationLevel.L1,))
        self.engine.mark_delivered(action)
        self.assertIsNone(self.engine.process(self.failure))

        self.clock.advance(30)
        action = self.engine.process(self.failure)
        self.assertEqual(action.kind, AlertKind.ESCALATION)
        self.assertEqual(action.levels, (EscalationLevel.L2,))
        self.engine.mark_delivered(action)

        self.clock.advance(30)
        action = self.engine.process(self.failure)
        self.assertEqual(action.levels, (EscalationLevel.L3,))
        self.engine.mark_delivered(action)

        action = self.engine.process(self.success)
        self.assertEqual(action.kind, AlertKind.RECOVERY)
        self.assertEqual(
            action.levels,
            (EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3),
        )
        self.engine.mark_delivered(action)
        self.assertIsNone(self.engine.process(self.success))

    def test_recovered_url_starts_a_new_l1_failure_lifecycle(self) -> None:
        action = self.engine.process(self.failure)
        self.engine.mark_delivered(action)
        self.engine.process(self.success)

        action = self.engine.process(self.failure)

        self.assertEqual(action.kind, AlertKind.FAILURE)
        self.assertEqual(action.levels, (EscalationLevel.L1,))

    def test_cache_persists_state_and_expires_recovered_urls(self) -> None:
        action = self.engine.process(self.failure)
        self.engine.mark_delivered(action)
        self.cache.save()
        reloaded = CacheManager(Path(self.temporary_directory.name), "test-activation")
        reloaded.load()
        self.assertTrue(reloaded.get("https://example.com").is_failing)

        reloaded_engine = AlertEngine(reloaded, escalation_settings(), 60, now=self.clock.now)
        reloaded_engine.process(self.success)
        self.clock.advance(61)
        reloaded_engine.prune({"https://example.com"})

        self.assertIsNone(reloaded.get("https://example.com"))

    def test_delivery_retries_only_recipients_without_a_confirmed_delivery(self) -> None:
        action = self.engine.process(self.failure)
        recipients = ["111", "222"]

        self.assertEqual(self.engine.begin_delivery(action, recipients), recipients)
        self.assertFalse(self.engine.record_delivery_results(action, recipients, {"111"}))
        self.cache.save()

        reloaded = CacheManager(Path(self.temporary_directory.name), "test-activation")
        reloaded.load()
        reloaded_engine = AlertEngine(reloaded, escalation_settings(), 60, now=self.clock.now)
        self.assertEqual(reloaded_engine.begin_delivery(action, recipients), ["222"])
        self.assertFalse(reloaded_engine.record_delivery_results(action, recipients, set()))
        self.assertEqual(reloaded_engine.begin_delivery(action, recipients), ["222"])
        self.assertFalse(reloaded_engine.record_delivery_results(action, recipients, set()))
        self.assertEqual(reloaded_engine.begin_delivery(action, recipients), [])

    def test_rejects_a_malformed_cache_root_with_a_clear_error(self) -> None:
        self.cache._cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache._cache_file.write_text("[]", encoding="utf-8")

        with self.assertRaisesRegex(CacheError, "Cache root must be an object"):
            self.cache.load()
