from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authentication"

    def ready(self):
        """Register signal handlers when the app is ready."""
        # Signals are automatically connected via @receiver decorators
        # Import signals module to ensure handlers are registered
        from . import signals  # noqa
