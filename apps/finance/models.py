"""
FleetFlow – Finance App Models.

Implements:
- Expense: operational cost entries (fuel, toll, repair, salary)
- Invoice: per-trip billing record enabling ROI calculation
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone

from apps.dispatch.models import Trip
from apps.fleet.models import Vehicle


class Expense(models.Model):
    """
    Records a single operational cost.

    Design rationale:
    - Linked optionally to a Trip OR Vehicle (not both required) because
      some costs (depot rent, admin salary) are not trip-specific.
    - Category enum enables filtering for financial reports.
    - Separate model (not fields on Trip) allows multiple expenses per trip
      and non-trip expenses in the same table.
    """

    class Category(models.TextChoices):
        FUEL = "FUEL", "Fuel"
        TOLL = "TOLL", "Toll / E-Way"
        REPAIR = "REPAIR", "Repairs"
        SALARY = "SALARY", "Driver Salary"
        INSURANCE = "INSURANCE", "Insurance Premium"
        MISC = "MISC", "Miscellaneous"

    trip = models.ForeignKey(
        Trip,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    category = models.CharField(
        max_length=20, choices=Category.choices, db_index=True
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    date = models.DateField(default=timezone.now, db_index=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="expenses_added",
    )
    receipt = models.FileField(upload_to="receipts/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["category", "date"]),
        ]

    def __str__(self) -> str:
        trip_ref = self.trip.trip_number if self.trip else "General"
        return f"{self.get_category_display()} – ₹{self.amount} ({trip_ref})"


class Invoice(models.Model):
    """
    Billing record for a completed trip.

    Design rationale:
    - OneToOne on Trip ensures exactly one invoice per trip.
    - Enables ROI = Invoice.amount_charged - total Expenses for the trip.
    - Kept separate from Trip to allow flexible billing workflows.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        OVERDUE = "OVERDUE", "Overdue"
        CANCELLED = "CANCELLED", "Cancelled"

    trip = models.OneToOneField(
        Trip, on_delete=models.CASCADE, related_name="invoice"
    )
    client_name = models.CharField(max_length=150)
    client_contact = models.CharField(max_length=100, blank=True)
    amount_charged = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    issued_at = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return f"INV-{self.trip.trip_number} | {self.client_name} | ₹{self.amount_charged}"

    @property
    def total_expenses(self):
        """Fetch sum of all expenses linked to this trip."""
        from django.db.models import Sum
        return (
            self.trip.expenses.aggregate(total=Sum("amount"))["total"] or 0
        )

    @property
    def roi(self):
        """Return on Investment = Revenue - Costs for this trip."""
        return self.amount_charged - self.total_expenses
