"""FleetFlow – dispatch AppConfig. Registers signals on app ready."""
from django.apps import AppConfig


class DispatchConfig(AppConfig):
    name = "apps.dispatch"
    verbose_name = "Dispatch & Trips"

    def ready(self):
        """Import signals so they are registered when Django starts."""
        import apps.dispatch.signals  # noqa: F401
