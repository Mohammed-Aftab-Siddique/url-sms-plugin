from dynatrace_extension import Extension, Status, StatusValue

from url_sms_plugin.config.settings import load_settings
from url_sms_plugin.config.validator import ConfigurationError, validate_settings


class ExtensionImpl(Extension):
    def initialize(self) -> None:
        """Load and validate the local activation configuration."""
        try:
            self.settings = load_settings(self.activation_config)
            validate_settings(self.settings)
        except ConfigurationError:
            self.logger.exception("URL SMS Plugin configuration is invalid.")
            raise

        self.logger.info(
            f"URL SMS Plugin initialized with {len(self.settings.urls)} configured URL(s); "
            f"dry run: {self.settings.dry_run}."
        )

    def query(self):
        """Confirm that the local configuration is ready for URL checks.

        URL checks, metrics, cache state, and SMS delivery are introduced in later stages.
        """
        self.logger.info(f"URL SMS Plugin query started for {len(self.settings.urls)} URL(s).")

        for target in self.settings.urls:
            self.logger.debug("URL check is configured for %s.", target.url)

        self.logger.info("URL SMS Plugin query completed.")

    def fastcheck(self) -> Status:
        return Status(StatusValue.OK)


def main():
    ExtensionImpl(name="url_sms_plugin").run()


if __name__ == "__main__":
    main()
