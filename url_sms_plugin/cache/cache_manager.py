"""Activation-isolated JSON cache with atomic writes."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from url_sms_plugin.models.alerting import EscalationLevel, UrlAlertState


class CacheError(RuntimeError):
    """Raised when durable alert state cannot be loaded or saved."""


class CacheManager:
    """Maintain URL states in a cache file isolated by activation ID."""

    def __init__(self, cache_dir: Path, activation_id: str) -> None:
        filename = hashlib.sha256(activation_id.encode("utf-8")).hexdigest() + ".json"
        self._cache_file = cache_dir / filename
        self._states: dict[str, UrlAlertState] = {}

    def load(self) -> None:
        """Load previous state if available; fail safely on malformed cache data."""
        if not self._cache_file.exists():
            return
        try:
            payload = json.loads(self._cache_file.read_text(encoding="utf-8"))
            self._states = {url: self._deserialize(url, item) for url, item in payload.items()}
        except (OSError, TypeError, ValueError, KeyError) as exc:
            raise CacheError(f"Unable to load URL alert cache: {exc}") from exc

    def save(self) -> None:
        """Persist state atomically so an interrupted write retains the old cache."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {url: self._serialize(state) for url, state in self._states.items()}
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self._cache_file.parent,
                delete=False,
            ) as temporary_file:
                json.dump(payload, temporary_file, sort_keys=True)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
                temporary_path = Path(temporary_file.name)
            temporary_path.replace(self._cache_file)
        except OSError as exc:
            raise CacheError(f"Unable to save URL alert cache: {exc}") from exc

    def get(self, url: str) -> UrlAlertState | None:
        return self._states.get(url)

    def put(self, state: UrlAlertState) -> None:
        self._states[state.url] = state

    def prune(self, configured_urls: set[str], now: datetime, retention_minutes: int) -> None:
        """Remove only recovered or no-longer-configured state older than retention."""
        cutoff = now.timestamp() - (retention_minutes * 60)
        self._states = {
            url: state
            for url, state in self._states.items()
            if self._should_retain(state, url in configured_urls, cutoff)
        }

    @staticmethod
    def _should_retain(state: UrlAlertState, is_configured: bool, cutoff: float) -> bool:
        if not state.is_failing:
            return state.recovered_at is not None and state.recovered_at.timestamp() >= cutoff
        return is_configured or state.last_seen_at.timestamp() >= cutoff

    @staticmethod
    def _serialize(state: UrlAlertState) -> dict[str, str | bool | None]:
        return {
            "is_failing": state.is_failing,
            "first_failed_at": state.first_failed_at.isoformat() if state.first_failed_at else None,
            "last_seen_at": state.last_seen_at.isoformat(),
            "highest_notified_level": (
                state.highest_notified_level.value if state.highest_notified_level else None
            ),
            "recovered_at": state.recovered_at.isoformat() if state.recovered_at else None,
            "recovery_notified": state.recovery_notified,
            "pending_action_key": state.pending_action_key,
            "delivery_attempts": state.delivery_attempts,
        }

    @staticmethod
    def _deserialize(url: str, item: dict[str, str | bool | None]) -> UrlAlertState:
        first_failed_at = item["first_failed_at"]
        recovered_at = item["recovered_at"]
        highest_notified_level = item["highest_notified_level"]
        return UrlAlertState(
            url=url,
            is_failing=bool(item["is_failing"]),
            first_failed_at=datetime.fromisoformat(first_failed_at) if first_failed_at else None,
            last_seen_at=datetime.fromisoformat(str(item["last_seen_at"])),
            highest_notified_level=(
                EscalationLevel(str(highest_notified_level)) if highest_notified_level else None
            ),
            recovered_at=datetime.fromisoformat(recovered_at) if recovered_at else None,
            recovery_notified=bool(item.get("recovery_notified", False)),
            pending_action_key=item.get("pending_action_key"),
            delivery_attempts=int(item.get("delivery_attempts", 0)),
        )
