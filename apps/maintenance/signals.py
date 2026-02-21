"""
FleetFlow – Maintenance Signals.

Controls vehicle status based on maintenance log state transitions.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from apps.maintenance.models import MaintenanceLog
from apps.fleet.models import Vehicle


@receiver(post_save, sender=MaintenanceLog)
def handle_maintenance_status_change(sender, instance: MaintenanceLog, created: bool, **kwargs):
    """
    Keep vehicle status in sync with its maintenance log.
    - New OPEN log → vehicle = IN_MAINTENANCE
    - Log moved to CLOSED → vehicle = AVAILABLE (if no other open logs)
    """
    vehicle_id = instance.vehicle_id

    if instance.status in (MaintenanceLog.Status.OPEN, MaintenanceLog.Status.IN_PROGRESS):
        transaction.on_commit(
            lambda: Vehicle.objects.filter(pk=vehicle_id).update(
                status=Vehicle.Status.IN_MAINTENANCE
            )
        )
    elif instance.status == MaintenanceLog.Status.CLOSED:
        # Only release vehicle if no other open logs exist
        def release_if_clear():
            still_open = MaintenanceLog.objects.filter(
                vehicle_id=vehicle_id,
            ).exclude(
                status=MaintenanceLog.Status.CLOSED
            ).exists()
            if not still_open:
                Vehicle.objects.filter(pk=vehicle_id).update(
                    status=Vehicle.Status.AVAILABLE
                )

        transaction.on_commit(release_if_clear)
