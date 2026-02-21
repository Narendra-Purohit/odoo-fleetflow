"""
FleetFlow – Dispatch Signals.

Decoupled side-effects fired after Trip and TripAssignment state changes.

Design rationale:
  Signals keep the dispatch, fleet, and users apps loosely coupled.
  Vehicle and Driver status updates happen here, not in TripService.save(),
  ensuring the fleet app does not need to import from dispatch.

Signal chain:
  Trip.save() → post_save(Trip)
    → if DISPATCHED: vehicle.status = ON_TRIP, driver.status = ON_TRIP
    → if COMPLETED/CANCELLED: vehicle.status = AVAILABLE, driver.status = AVAILABLE
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from apps.dispatch.models import Trip
from apps.fleet.models import Vehicle
from apps.dispatch.models import Driver


@receiver(post_save, sender=Trip)
def handle_trip_status_change(sender, instance: Trip, **kwargs):
    """
    React to Trip status changes by updating the assigned vehicle and driver.
    Wrapped in on_commit to ensure the assignment exists before we read it.
    """
    # Only act if an assignment exists
    assignment = getattr(instance, "assignment", None)
    if assignment is None:
        return

    status = instance.status

    if status == Trip.Status.DISPATCHED:
        transaction.on_commit(
            lambda: _set_vehicle_driver_status(
                assignment.vehicle_id,
                assignment.driver_id,
                vehicle_status=Vehicle.Status.ON_TRIP,
                driver_status=Driver.Status.ON_TRIP,
            )
        )

    elif status in (Trip.Status.COMPLETED, Trip.Status.CANCELLED):
        transaction.on_commit(
            lambda: _set_vehicle_driver_status(
                assignment.vehicle_id,
                assignment.driver_id,
                vehicle_status=Vehicle.Status.AVAILABLE,
                driver_status=Driver.Status.AVAILABLE,
            )
        )


def _set_vehicle_driver_status(
    vehicle_id: int,
    driver_id: int,
    vehicle_status: str,
    driver_status: str,
) -> None:
    """Update vehicle and driver status atomically."""
    with transaction.atomic():
        Vehicle.objects.filter(pk=vehicle_id).update(status=vehicle_status)
        Driver.objects.filter(pk=driver_id).update(status=driver_status)
