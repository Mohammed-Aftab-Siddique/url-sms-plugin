from pathlib import Path

from dynatrace_extension import Extension, Status, StatusValue

from url_sms_plugin.cache.cache_manager import CacheManager
from url_sms_plugin.clients.sms_client import SmsClient
from url_sms_plugin.clients.url_client import UrlAvailabilityClient
from url_sms_plugin.config.settings import load_settings
from url_sms_plugin.config.validator import ConfigurationError, validate_settings
from url_sms_plugin.metrics.publisher import MetricsPublisher
from url_sms_plugin.processing.alert_engine import AlertEngine
from url_sms_plugin.processing.notification_service import NotificationService


class ExtensionImpl(Extension):
    def schedule(self, callback, interval, args=None, activation_type=None, offset_seconds=None):
        """Use activation-configured cadence for the SDK's default query callback."""
        if getattr(self, "settings", None) and callback == self.query:
            interval = self.settings.polling_interval
        return super().schedule(callback, interval, args, activation_type, offset_seconds)

    def initialize(self) -> None:
        """Load and validate the local activation configuration."""
        try:
            self.settings = load_settings(self.activation_config)
            validate_settings(self.settings)
            self.url_client = UrlAvailabilityClient()
            self.metrics = MetricsPublisher(self)
            self.cache = CacheManager(Path(), self.monitoring_config_id)
            self.cache.load()
            self.alert_engine = AlertEngine(
                self.cache,
                self.settings.escalation,
                self.settings.cache_retention_minutes,
            )
            self.notifications = NotificationService(
                SmsClient(self.settings.sms_api, self.settings.dry_run),
                self.settings.escalation,
            )
        except ConfigurationError:
            self.logger.exception("URL SMS Plugin configuration is invalid.")
            raise

        self.logger.info(
            f"URL SMS Plugin initialized with {len(self.settings.urls)} configured URL(s); "
            f"dry run: {self.settings.dry_run}."
        )

    def query(self):
        """Check each configured URL and log its normalized availability result."""
        self.logger.info(f"URL SMS Plugin query started for {len(self.settings.urls)} URL(s).")

        for target in self.settings.urls:
            result = self.url_client.check(target.url, self.settings.max_redirects)
            self.metrics.url_status(result)
            action = self.alert_engine.process(result)
            if action:
                levels = ", ".join(level.value for level in action.levels)
                self.logger.info(
                    f"Alert decision: kind={action.kind.value}, url={action.url}, "
                    f"status={action.status_code}, levels={levels}."
                )
                if self.settings.dry_run:
                    self.logger.info("Dry run: SMS action retained as pending.")
                else:
                    recipients = self.notifications.recipients(action)
                    pending = self.alert_engine.begin_delivery(action, recipients)
                    self.cache.save()
                    delivered = self.notifications.dispatch(action, pending)
                    action_complete = self.alert_engine.record_delivery_results(action, recipients, delivered)
                    self.cache.save()
                    if action_complete:
                        self.alert_engine.mark_delivered(action)
                        self.cache.save()
                        self.logger.info(f"SMS action delivered: kind={action.kind.value}, url={action.url}.")
                    elif not pending:
                        self.logger.warning("SMS action exhausted its three delivery attempts.")
                    else:
                        self.logger.warning("SMS action remains pending after a delivery failure.")
            error = result.error.label if result.error else "none"
            self.logger.info(
                f"URL check completed: url={result.url}, status={result.status_code}, "
                f"attempts={result.attempts}, error={error}."
            )

        self.alert_engine.prune({target.url for target in self.settings.urls})
        self.cache.save()
        self.logger.info("URL SMS Plugin query completed.")

    def fastcheck(self) -> Status:
        return Status(StatusValue.OK)


def main():
    ExtensionImpl(name="url_sms_plugin").run()


if __name__ == "__main__":
    main()
