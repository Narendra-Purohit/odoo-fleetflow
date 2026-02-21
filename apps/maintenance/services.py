"""
FleetFlow – Maintenance Service Layer.

Wraps all maintenance log state changes in @transaction.atomic to
guarantee that the vehicle status update (via signal) and the log save
either both succeed or both roll back — preventing partial-state bugs
where a log is created but the vehicle remains AVAILABLE.
"""
import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.maintenance.models import MaintenanceLog

logger = logging.getLogger(__name__)


class MaintenanceService:
    """
    Orchestrates maintenance log lifecycle with strict atomicity.

    All methods use @transaction.atomic so that:
    - The log save and the vehicle status change (via signal) are one unit.
    - Any failure rolls back both, preventing partial state corruption.
    """

    @staticmethod
    @transaction.atomic
    def open_log(
        vehicle,
        service_type: str,
        description: str,
        logged_by,
        start_date=None,
        vendor: str = "",
        notes: str = "",
    ) -> MaintenanceLog:
        """
        Create a new OPEN maintenance log for a vehicle.

        Atomically creates the log and transitions vehicle to IN_MAINTENANCE
        via the post_save signal. If any step fails, both roll back.

        Args:
            vehicle: The Vehicle instance to log maintenance for.
            service_type: One of MaintenanceLog.ServiceType choices.
            description: Human-readable description of the maintenance work.
            logged_by: The CustomUser creating this record.
            start_date: Date maintenance begins (defaults to today).
            vendor: Name of the service provider (optional).
            notes: Additional notes (optional).

        Returns:
            The newly created MaintenanceLog instance.

        Raises:
            ValidationError: If the vehicle is already DECOMMISSIONED.
        """
        from apps.fleet.models import Vehicle

        # Prevent opening maintenance on a decommissioned vehicle
        if vehicle.status == Vehicle.Status.DECOMMISSIONED:
            raise ValidationError(
                f"Cannot open a maintenance log for decommissioned vehicle "
                f"'{vehicle.plate_number}'."
            )

        log = MaintenanceLog(
            vehicle=vehicle,
            service_type=service_type,
            status=MaintenanceLog.Status.OPEN,
            description=description,
            logged_by=logged_by,
            start_date=start_date or timezone.now().date(),
            vendor=vendor,
            notes=notes,
        )
        log.save()  # post_save signal fires → vehicle → IN_MAINTENANCE (via on_commit)
        logger.info(
            "Maintenance log %s opened for vehicle %s by %s",
            log.pk, vehicle.plate_number, logged_by,
        )
        return log

    @staticmethod
    @transaction.atomic
    def close_log(log: MaintenanceLog, cost: float = None, notes: str = "") -> MaintenanceLog:
        """
        Close an open maintenance log and release the vehicle back to AVAILABLE.

        Atomically updates the log status and triggers the on_commit vehicle
        state change via the post_save signal.

        Args:
            log: The MaintenanceLog instance to close.
            cost: Final maintenance cost in INR (optional update).
            notes: Closing notes (optional).

        Returns:
            The updated MaintenanceLog instance.

        Raises:
            ValidationError: If the log is already closed.
        """
        if log.status == MaintenanceLog.Status.CLOSED:
            raise ValidationError(
                f"Maintenance log #{log.pk} is already closed."
            )

        log.status = MaintenanceLog.Status.CLOSED
        log.end_date = timezone.now().date()
        if cost is not None:
            log.cost = cost
        if notes:
            log.notes = notes
        log.save()  # post_save signal → vehicle → AVAILABLE (via on_commit)
        logger.info(
            "Maintenance log %s closed for vehicle %s. Cost: %s",
            log.pk, log.vehicle.plate_number, log.cost,
        )
        return log
