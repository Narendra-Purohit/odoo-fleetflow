"""
FleetFlow – Fleet App Models.

Implements:
- Vehicle: core fleet asset with strict status enum
- VehicleDocument: insurance/registration/inspection tracking
- FuelLog: per-fill fuel consumption records (enables efficiency calc)
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings

class VehicleQuerySet(models.QuerySet):
    """Reusable filtered querysets for vehicle availability lookups."""

    def available(self):
        """Return only vehicles eligible for dispatch."""
        return self.filter(status=Vehicle.Status.AVAILABLE)

    def in_shop(self):
        """Return vehicles currently under maintenance."""
        return self.filter(status=Vehicle.Status.IN_MAINTENANCE)

    def active(self):
        """Exclude permanently decommissioned vehicles."""
        return self.exclude(status=Vehicle.Status.DECOMMISSIONED)


class VehicleManager(models.Manager):
    """Default manager returning a VehicleQuerySet for chainable filters."""

    def get_queryset(self):
        return VehicleQuerySet(self.model, using=self._db)

    def available(self):
        return self.get_queryset().available()



class Vehicle(models.Model):
    """
    Represents a single fleet vehicle.

    Design rationale:
    - status is a strict enum; no free-form strings allowed.
    - max_capacity_kg is the source of truth for cargo weight validation.
    - odometer_km is updated on each trip completion for efficiency tracking.
    - acquisition_cost enables ROI calculation: (revenue - costs) / acquisition_cost.
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ON_TRIP = "ON_TRIP", "On Trip"
        IN_MAINTENANCE = "IN_MAINTENANCE", "In Maintenance"
        DECOMMISSIONED = "DECOMMISSIONED", "Decommissioned"

    class FuelType(models.TextChoices):
        DIESEL = "DIESEL", "Diesel"
        PETROL = "PETROL", "Petrol"
        CNG = "CNG", "CNG"
        ELECTRIC = "ELECTRIC", "Electric"

    plate_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Vehicle registration plate number.",
    )
    make = models.CharField(max_length=60)
    model = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField()
    color = models.CharField(max_length=30, blank=True)
    vin = models.CharField(
        max_length=17, unique=True, blank=True, null=True,
        help_text="17-char Vehicle Identification Number.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True,
    )
    fuel_type = models.CharField(
        max_length=10, choices=FuelType.choices, default=FuelType.DIESEL
    )
    max_capacity_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Maximum payload capacity in kilograms.",
    )
    odometer_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Current odometer reading in kilometres.",
    )
    notes = models.TextField(blank=True)
    acquisition_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Purchase/lease cost of this vehicle in INR. Required for ROI calculation.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vehicles_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        ordering = ["plate_number"]
        indexes = [
            models.Index(fields=["status", "fuel_type"]),
        ]

    objects = VehicleManager()

    def __str__(self) -> str:
        return f"{self.plate_number} – {self.make} {self.model} ({self.year})"

    def clean(self):
        """
        Enforce immutability of DECOMMISSIONED vehicles.
        A decommissioned vehicle must never be reassigned to any other status.
        """
        if self.pk:
            try:
                original = Vehicle.objects.get(pk=self.pk)
                if original.status == self.Status.DECOMMISSIONED and self.status != self.Status.DECOMMISSIONED:
                    raise ValidationError(
                        {"status": "A decommissioned vehicle cannot be returned to service."}
                    )
            except Vehicle.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_available(self) -> bool:
        """Business rule helper: only AVAILABLE vehicles can be assigned."""
        return self.status == self.Status.AVAILABLE

    def set_status(self, new_status: str, save: bool = True) -> None:
        """
        Controlled status transition — validates enum membership.
        Used by the service layer to avoid raw field assignments.
        """
        valid = [choice[0] for choice in self.Status.choices]
        if new_status not in valid:
            raise ValueError(f"Invalid vehicle status: {new_status}")
        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])


class VehicleDocument(models.Model):
    """
    Tracks compliance documents per vehicle.

    Design rationale: Separate model allows multiple doc types per vehicle,
    expiry tracking, and future attachment of file scan uploads.
    """

    class DocType(models.TextChoices):
        INSURANCE = "INSURANCE", "Insurance"
        REGISTRATION = "REGISTRATION", "Registration"
        INSPECTION = "INSPECTION", "Fitness/Inspection"
        PERMIT = "PERMIT", "Route Permit"

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    document_number = models.CharField(max_length=100, blank=True)
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(db_index=True)
    file = models.FileField(upload_to="vehicle_docs/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vehicle Document"
        verbose_name_plural = "Vehicle Documents"
        unique_together = [("vehicle", "doc_type")]
        ordering = ["expires_on"]

    def __str__(self) -> str:
        return f"{self.vehicle.plate_number} – {self.get_doc_type_display()}"


class FuelLog(models.Model):
    """
    Records each fuel fill-up for a vehicle.

    Design rationale: Keeping fuel logs separate from trips allows fill-ups
    outside of trip contexts (parked vehicles, depot fills). Enables accurate
    fuel efficiency calculations via odometer deltas.
    """

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="fuel_logs"
    )
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fuel_logs_entered",
    )
    date = models.DateField(db_index=True)
    liters = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    cost_per_liter = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(0)]
    )
    odometer_at_fill = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Odometer reading at the time of this fill-up.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fuel Log"
        verbose_name_plural = "Fuel Logs"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.vehicle.plate_number} – {self.liters}L on {self.date}"

    @property
    def total_cost(self):
        """Compute total cost of this fill-up."""
        return self.liters * self.cost_per_liter
