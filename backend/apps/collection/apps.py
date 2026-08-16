from django.apps import AppConfig


class CollectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.collection"

    def ready(self):
        from .provisioning import load_starter_deck_definitions

        # Invalid or missing bundled manifests must fail before signups are served.
        load_starter_deck_definitions()
        from . import signals  # noqa: F401
