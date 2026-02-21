"""
FleetFlow – TripService (Dispatch Service Layer).

Centralises all trip state transitions with:
- select_for_update() to prevent race conditions on concurrent assignment
- transaction.atomic() to guarantee atomicity across related model saves
- Clear separation from views: views call services, never manipulate models directly

Design rationale:
  Putting this logic in the service layer (not views or models) means:
  - It can be called from management commands, admin actions, or future APIs
  - Transaction boundaries are explicit and testable
  - Views stay thin
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.dispatch.models import Trip, TripAssignment, Driver
from apps.fleet.models import Vehicle


class TripService:
    """
    Business logic for trip lifecycle management.
    All methods are classmethods – no instance state needed.
    """

    @classmethod
    @transaction.atomic
    def assign_trip(
        cls,
        trip: Trip,
        vehicle_id: int,
        driver_id: int,
        assigned_by,
    ) -> TripAssignment:
        """
        Assign a vehicle and driver to a trip.

        Uses select_for_update() to lock the vehicle and driver rows
        for the duration of the transaction, preventing double-booking
        in concurrent requests.

        Raises:
            ValidationError: if any business rule is violated.
            ValueError: if trip is not in PLANNED status.
        """
        if trip.status != Trip.Status.PLANNED:
            raise ValueError(
                f"Cannot assign trip '{trip.trip_number}' in status '{trip.status}'."
            )

        # Lock rows to prevent race conditions
        vehicle = Vehicle.objects.select_for_update().get(pk=vehicle_id)
        driver = Driver.objects.select_for_update().get(pk=driver_id)

        # Check for existing assignment and delete (reassignment scenario)
        TripAssignment.objects.filter(trip=trip).delete()

        assignment = TripAssignment(
            trip=trip,
            vehicle=vehicle,
            driver=driver,
            assigned_by=assigned_by,
        )
        # full_clean() inside TripAssignment.save() enforces all business rules
        assignment.save()
        return assignment

    @classmethod
    @transaction.atomic
    def dispatch_trip(cls, trip: Trip, actor=None) -> Trip:
        """
        Transition trip PLANNED → DISPATCHED.
        Triggers post_save signal that sets vehicle/driver to ON_TRIP.

        Raises:
            ValueError: if trip cannot transition or has no assignment.
        """
        if not hasattr(trip, "assignment"):
            raise ValueError(
                f"Trip '{trip.trip_number}' has no vehicle/driver assignment. Assign first."
            )
        trip.transition_to(Trip.Status.DISPATCHED, actor=actor)
        return trip

    @classmethod
    @transaction.atomic
    def mark_in_transit(cls, trip: Trip, actor=None) -> Trip:
        """Transition trip DISPATCHED → IN_TRANSIT."""
        trip.transition_to(Trip.Status.IN_TRANSIT, actor=actor)
        return trip

    @classmethod
    @transaction.atomic
    def complete_trip(cls, trip: Trip, final_odometer: float = None, actor=None) -> Trip:
        """
        Transition trip IN_TRANSIT → COMPLETED.
        Optionally updates vehicle odometer to enable fuel efficiency calc.
        Triggers post_save signal that sets vehicle/driver back to AVAILABLE.

        Args:
            final_odometer: If provided, updates vehicle odometer reading.
        """
        trip.transition_to(Trip.Status.COMPLETED, actor=actor)

        if final_odometer is not None and hasattr(trip, "assignment"):
            vehicle = trip.assignment.vehicle
            vehicle.odometer_km = final_odometer
            vehicle.save(update_fields=["odometer_km", "updated_at"])

        return trip

    @classmethod
    @transaction.atomic
    def cancel_trip(cls, trip: Trip, actor=None) -> Trip:
        """Transition trip to CANCELLED from any non-terminal status."""
        trip.transition_to(Trip.Status.CANCELLED, actor=actor)
        return trip
