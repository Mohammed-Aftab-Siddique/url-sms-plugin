"""Stateful decisions for URL failure, escalation, and recovery alerts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from url_sms_plugin.cache.cache_manager import CacheManager
from url_sms_plugin.models.alerting import AlertAction, AlertKind, EscalationLevel, UrlAlertState
from url_sms_plugin.models.settings import EscalationSettings
from url_sms_plugin.models.url_check import UrlCheckResult
from url_sms_plugin.processing.escalation import current_level, levels_through


class AlertEngine:
    """Produce at most one action for each observed URL state transition."""

    def __init__(
        self,
        cache: CacheManager,
        settings: EscalationSettings,
        cache_retention_minutes: int,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._cache = cache
        self._settings = settings
        self._cache_retention_minutes = cache_retention_minutes
        self._now = now or (lambda: datetime.now(ZoneInfo("Asia/Kolkata")))

    def process(self, result: UrlCheckResult) -> AlertAction | None:
        """Store the result and return an action only for a required transition."""
        now = self._now()
        state = self._cache.get(result.url)
        if result.is_available:
            return self._handle_available(result, state, now)
        return self._handle_failure(result, state, now)

    def prune(self, configured_urls: set[str]) -> None:
        """Drop recovered or removed URL states after configured retention."""
        self._cache.prune(configured_urls, self._now(), self._cache_retention_minutes)

    def mark_delivered(self, action: AlertAction) -> None:
        """Commit an action only after the SMS transport confirms delivery."""
        state = self._cache.get(action.url)
        if state is None:
            return
        if action.kind == AlertKind.RECOVERY:
            self._cache.put(
                UrlAlertState(
                    url=state.url,
                    is_failing=False,
                    first_failed_at=state.first_failed_at,
                    last_seen_at=state.last_seen_at,
                    highest_notified_level=state.highest_notified_level,
                    recovered_at=state.recovered_at,
                    recovery_notified=True,
                )
            )
            return
        self._cache.put(
            UrlAlertState(
                url=state.url,
                is_failing=True,
                first_failed_at=state.first_failed_at,
                last_seen_at=state.last_seen_at,
                highest_notified_level=action.levels[-1],
            )
        )

    def _handle_failure(
        self,
        result: UrlCheckResult,
        state: UrlAlertState | None,
        now: datetime,
    ) -> AlertAction | None:
        if state is None or not state.is_failing:
            self._cache.put(
                UrlAlertState(
                    url=result.url,
                    is_failing=True,
                    first_failed_at=now,
                    last_seen_at=now,
                    highest_notified_level=None,
                )
            )
            return AlertAction(result.url, result.status_code, AlertKind.FAILURE, (EscalationLevel.L1,))

        level = current_level(state.first_failed_at, now, self._settings)
        updated = UrlAlertState(
            url=state.url,
            is_failing=True,
            first_failed_at=state.first_failed_at,
            last_seen_at=now,
            highest_notified_level=state.highest_notified_level,
        )
        self._cache.put(updated)
        if state.highest_notified_level is not None and level <= state.highest_notified_level:
            return None
        return AlertAction(result.url, result.status_code, AlertKind.ESCALATION, (level,))

    def _handle_available(
        self,
        result: UrlCheckResult,
        state: UrlAlertState | None,
        now: datetime,
    ) -> AlertAction | None:
        if state is None:
            return None
        if not state.is_failing:
            if state.highest_notified_level is None or state.recovery_notified:
                return None
            return AlertAction(
                result.url,
                result.status_code,
                AlertKind.RECOVERY,
                levels_through(state.highest_notified_level),
            )

        if state.highest_notified_level is None:
            self._cache.put(
                UrlAlertState(
                    url=state.url,
                    is_failing=False,
                    first_failed_at=state.first_failed_at,
                    last_seen_at=now,
                    highest_notified_level=None,
                    recovered_at=now,
                )
            )
            return None

        recovered = UrlAlertState(
            url=state.url,
            is_failing=False,
            first_failed_at=state.first_failed_at,
            last_seen_at=now,
            highest_notified_level=state.highest_notified_level,
            recovered_at=now,
        )
        self._cache.put(recovered)
        return AlertAction(
            result.url,
            result.status_code,
            AlertKind.RECOVERY,
            levels_through(state.highest_notified_level),
        )
