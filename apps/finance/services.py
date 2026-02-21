"""
FleetFlow – Finance Service Layer.

Centralises financial calculations to avoid N+1 queries in templates
and ensure formulas are computed in one place.

Financial Formulas:
    Total Operational Cost = SUM(Fuel Cost) + SUM(Maintenance Cost)
    Fuel Efficiency        = total_km / total_liters
    Vehicle ROI            = (revenue - total_operational_cost) / acquisition_cost
"""
import logging
from decimal import Decimal

from django.db.models import Sum, F, ExpressionWrapper, DecimalField

logger = logging.getLogger(__name__)


class FinanceService:
    """
    Financial aggregation and ROI calculation service.

    All methods accept model instances and return Decimal values.
    Designed to be called from views or management commands — never
    from templates or models.
    """

    @staticmethod
    def total_fuel_cost(vehicle) -> Decimal:
        """
        Calculate total fuel expenditure for a vehicle.

        SUM(liters * cost_per_liter) across all FuelLog entries.
        Uses a single DB aggregation — no Python-side iteration.

        Args:
            vehicle: Vehicle instance.

        Returns:
            Total fuel cost as Decimal. Returns 0 if no fuel logs exist.
        """
        result = vehicle.fuel_logs.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("liters") * F("cost_per_liter"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["total"]
        return result or Decimal("0")

    @staticmethod
    def total_maintenance_cost(vehicle) -> Decimal:
        """
        Calculate total maintenance expenditure for a vehicle.

        SUM(cost) across all MaintenanceLog entries.

        Args:
            vehicle: Vehicle instance.

        Returns:
            Total maintenance cost as Decimal.
        """
        result = vehicle.maintenance_logs.aggregate(total=Sum("cost"))["total"]
        return result or Decimal("0")

    @staticmethod
    def total_operational_cost(vehicle) -> Decimal:
        """
        Total Operational Cost = SUM(Fuel Cost) + SUM(Maintenance Cost).

        Args:
            vehicle: Vehicle instance.

        Returns:
            Combined operational cost as Decimal.
        """
        return (
            FinanceService.total_fuel_cost(vehicle)
            + FinanceService.total_maintenance_cost(vehicle)
        )

    @staticmethod
    def fuel_efficiency(vehicle) -> Decimal | None:
        """
        Fuel Efficiency = total distance travelled / total liters used.

        Computed across all completed trips for this vehicle.

        Args:
            vehicle: Vehicle instance.

        Returns:
            km/liter as Decimal, or None if insufficient data.
        """
        from apps.dispatch.models import Trip

        trip_data = Trip.objects.filter(
            assignment__vehicle=vehicle,
            status=Trip.Status.COMPLETED,
            distance_km__isnull=False,
        ).aggregate(total_km=Sum("distance_km"))

        fuel_data = vehicle.fuel_logs.aggregate(total_liters=Sum("liters"))

        total_km = trip_data["total_km"] or Decimal("0")
        total_liters = fuel_data["total_liters"] or Decimal("0")

        if total_liters == 0:
            return None
        return round(total_km / total_liters, 2)

    @staticmethod
    def vehicle_roi(vehicle) -> Decimal | None:
        """
        Vehicle ROI = (Revenue - Total Operational Cost) / Acquisition Cost.

        Requires:
        - vehicle.acquisition_cost to be set (non-null).
        - At least one PAID Invoice linked to a completed trip for this vehicle.

        Args:
            vehicle: Vehicle instance.

        Returns:
            ROI ratio as Decimal, or None if acquisition_cost is missing.
        """
        from apps.finance.models import Invoice

        if not vehicle.acquisition_cost:
            logger.warning(
                "ROI cannot be computed for vehicle %s: acquisition_cost is not set.",
                vehicle.plate_number,
            )
            return None

        revenue = (
            Invoice.objects.filter(
                trip__assignment__vehicle=vehicle,
                status=Invoice.Status.PAID,
            ).aggregate(total=Sum("amount_charged"))["total"]
            or Decimal("0")
        )

        op_cost = FinanceService.total_operational_cost(vehicle)
        return round((revenue - op_cost) / vehicle.acquisition_cost, 4)
