"""
FleetFlow – Maintenance App Models.

Implements:
- MaintenanceLog: historical repair/service records
- MaintenanceSchedule: proactive service scheduling by km/day intervals
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone

from apps.fleet.models import Vehicle


class MaintenanceLog(models.Model):
    """
    Records a maintenance event (repair, service, inspection).

    Design rationale:
    - Separate from MaintenanceSchedule — logs are historical facts,
      schedules are future-looking obligations.
    - Opening a log transitions the vehicle to IN_MAINTENANCE via signal.
    - Closing (status → CLOSED) transitions vehicle back to AVAILABLE.
    - cost field enables financial rollup in the analytics app.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        CLOSED = "CLOSED", "Closed"

    class ServiceType(models.TextChoices):
        REPAIR = "REPAIR", "Repair"
        ROUTINE = "ROUTINE", "Routine Service"
        INSPECTION = "INSPECTION", "Safety Inspection"
        TYRE = "TYRE", "Tyre Replacement"
        ACCIDENT = "ACCIDENT", "Accident Repair"
        OTHER = "OTHER", "Other"

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="maintenance_logs"
    )
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="maintenance_logs_created",
    )
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.ROUTINE,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    description = models.TextField()
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total maintenance cost in INR.",
    )
    vendor = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Maintenance Log"
        verbose_name_plural = "Maintenance Logs"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["status", "vehicle"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.vehicle.plate_number} – "
            f"{self.get_service_type_display()} ({self.get_status_display()})"
        )

    @property
    def duration_days(self):
        """Number of days the vehicle was in maintenance."""
        end = self.end_date or timezone.now().date()
        return (end - self.start_date).days


class MaintenanceSchedule(models.Model):
    """
    Forward-looking maintenance obligation per vehicle.

    Design rationale: Decoupled from MaintenanceLog to allow schedule
    management independent of completed work. next_due_at is auto-computed
    from last_done_at + interval to avoid stale data.
    """

    class Interval(models.TextChoices):
        KM_BASED = "KM", "Kilometre-based"
        DAY_BASED = "DAYS", "Day-based"
        BOTH = "BOTH", "Whichever comes first"

    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="maintenance_schedules"
    )
    service_type = models.CharField(
        max_length=20,
        choices=MaintenanceLog.ServiceType.choices,
        default=MaintenanceLog.ServiceType.ROUTINE,
    )
    interval_type = models.CharField(
        max_length=10, choices=Interval.choices, default=Interval.DAY_BASED
    )
    interval_km = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Kilometre interval for scheduled service.",
    )
    interval_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Day interval for scheduled service.",
    )
    last_done_at = models.DateField(null=True, blank=True)
    next_due_at = models.DateField(db_index=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Maintenance Schedule"
        verbose_name_plural = "Maintenance Schedules"
        ordering = ["next_due_at"]

    def __str__(self) -> str:
        return (
            f"{self.vehicle.plate_number} – "
            f"{self.get_service_type_display()} due {self.next_due_at}"
        )
