"""FleetFlow – maintenance AppConfig. Registers signals on app ready."""
from django.apps import AppConfig


class MaintenanceConfig(AppConfig):
    name = "apps.maintenance"
    verbose_name = "Maintenance"

    def ready(self):
        import apps.maintenance.signals  # noqa: F401
