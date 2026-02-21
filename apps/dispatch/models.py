"""
FleetFlow – Dispatch App Models.

Implements:
- Driver: operator with license validity and suspension status
- Trip: the core logistics entity with strict state machine
- TripAssignment: atomic vehicle+driver assignment per trip (separate for audit trail)
- Cargo: multi-item manifest per trip enabling weight aggregation rule
"""
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone

from apps.fleet.models import Vehicle


class Driver(models.Model):
    """
    Represents a licensed vehicle operator.

    Design rationale: 1-1 with CustomUser to leverage Django auth
    while keeping driver-specific fields (license, suspension) isolated.
    is_suspended is a separate boolean from status to make suspension
    checks explicit and catch it before status checks.
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ON_TRIP = "ON_TRIP", "On Trip"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        INACTIVE = "INACTIVE", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
    )
    license_number = models.CharField(max_length=50, unique=True, db_index=True)
    license_expires_on = models.DateField(db_index=True)
    license_class = models.CharField(
        max_length=20, blank=True,
        help_text="e.g. LMV, HMV, Transport",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    is_suspended = models.BooleanField(
        default=False,
        help_text="Administratively suspended – blocks all trip assignments.",
    )
    phone = models.CharField(max_length=20, blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Driver"
        verbose_name_plural = "Drivers"
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self) -> str:
        return f"{self.user.full_name} [{self.license_number}]"

    @property
    def is_license_valid(self) -> bool:
        """Check if the driver's license has not expired."""
        return self.license_expires_on >= timezone.now().date()

    @property
    def is_available_for_assignment(self) -> bool:
        """Composite eligibility check used by the service layer."""
        return (
            self.status == self.Status.AVAILABLE
            and not self.is_suspended
            and self.is_license_valid
        )

    def set_status(self, new_status: str, save: bool = True) -> None:
        """Controlled status transition with enum validation."""
        valid = [c[0] for c in self.Status.choices]
        if new_status not in valid:
            raise ValueError(f"Invalid driver status: {new_status}")
        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])


class Trip(models.Model):
    """
    Core logistics entity representing a single delivery/transport job.

    Design rationale:
    - trip_number uses UUID to ensure globally unique, unpredictable IDs.
    - Strict TextChoices enum prevents invalid status strings.
    - Timestamps (dispatched_at, completed_at) provide full audit trail.
    - created_by FK enables dispatcher accountability.
    """

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        DISPATCHED = "DISPATCHED", "Dispatched"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    trip_number = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Auto-generated unique trip reference.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
    )
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField(db_index=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="trips_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Trip"
        verbose_name_plural = "Trips"
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def save(self, *args, **kwargs):
        """Auto-generate trip_number before first save."""
        if not self.trip_number:
            self.trip_number = f"TRP-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.trip_number} ({self.get_status_display()})"

    # ── State machine helpers ─────────────────────────────────────────────────

    VALID_TRANSITIONS = {
        Status.PLANNED: [Status.DISPATCHED, Status.CANCELLED],
        Status.DISPATCHED: [Status.IN_TRANSIT, Status.CANCELLED],
        Status.IN_TRANSIT: [Status.COMPLETED, Status.CANCELLED],
        Status.COMPLETED: [],
        Status.CANCELLED: [],
    }

    def can_transition_to(self, new_status: str) -> bool:
        """Validate whether the requested status transition is legal."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_to(self, new_status: str, actor=None) -> None:
        """
        Perform a validated status transition.
        Raises ValueError on illegal transitions.
        This method is ALWAYS called through TripService to ensure
        atomicity and side-effect signals are properly fired.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition trip from '{self.status}' to '{new_status}'."
            )
        self.status = new_status
        if new_status == self.Status.DISPATCHED:
            self.dispatched_at = timezone.now()
        elif new_status == self.Status.COMPLETED:
            self.completed_at = timezone.now()
        self.save()


class TripAssignment(models.Model):
    """
    Links a Trip to a specific Vehicle and Driver.

    Design rationale:
    - OneToOne on Trip enforces exactly one active assignment per trip.
    - Kept separate from Trip to maintain assignment audit history and
      allow future reassignment modelling.
    - clean() enforces all business rules before any save.
    """

    trip = models.OneToOneField(
        Trip, on_delete=models.CASCADE, related_name="assignment"
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name="assignments"
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.PROTECT, related_name="assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignments_made",
    )

    class Meta:
        verbose_name = "Trip Assignment"
        verbose_name_plural = "Trip Assignments"

    def __str__(self) -> str:
        return f"{self.trip} → {self.vehicle} / {self.driver}"

    def clean(self):
        """
        Business rule enforcement before save.

        Rules enforced here (model layer) so they apply to both
        form submissions and programmatic saves:
        1. Driver must not be suspended.
        2. Driver license must not be expired.
        3. Driver must be AVAILABLE.
        4. Vehicle must be AVAILABLE.
        5. Total cargo weight must not exceed vehicle capacity.
        """
        errors = {}

        # Rule 1 – driver suspension
        if self.driver.is_suspended:
            errors["driver"] = (
                f"Driver '{self.driver}' is administratively suspended."
            )

        # Rule 2 – license validity
        if not self.driver.is_license_valid:
            errors.setdefault("driver", "")
            errors["driver"] += (
                f" Driver license expired on {self.driver.license_expires_on}."
            )

        # Rule 3 – driver availability
        if self.driver.status != Driver.Status.AVAILABLE:
            errors.setdefault("driver", "")
            errors["driver"] += (
                f" Driver is currently '{self.driver.get_status_display()}'."
            )

        # Rule 4 – vehicle availability
        if not self.vehicle.is_available:
            errors["vehicle"] = (
                f"Vehicle '{self.vehicle}' is currently '{self.vehicle.get_status_display()}'."
            )

        # Rule 5 – cargo weight
        if self.trip_id:
            total_weight = (
                self.trip.cargo_items.aggregate(
                    total=models.Sum("weight_kg")
                )["total"]
                or 0
            )
            if total_weight > self.vehicle.max_capacity_kg:
                errors["vehicle"] = (
                    f"Total cargo weight {total_weight} kg exceeds vehicle "
                    f"capacity of {self.vehicle.max_capacity_kg} kg."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Always run full_clean before saving to enforce business rules."""
        self.full_clean()
        super().save(*args, **kwargs)


class Cargo(models.Model):
    """
    Represents individual cargo items on a trip manifest.

    Design rationale: Multi-item cargo per trip (not a single weight field
    on Trip) enables detailed manifests and accurate aggregation for the
    weight validation rule. is_hazardous enables future regulatory checks.
    """

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="cargo_items"
    )
    description = models.CharField(max_length=255)
    weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    volume_m3 = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    quantity = models.PositiveIntegerField(default=1)
    is_hazardous = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Cargo Item"
        verbose_name_plural = "Cargo Items"

    def __str__(self) -> str:
        return f"{self.description} ({self.weight_kg} kg) on {self.trip.trip_number}"
