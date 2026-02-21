"""
FleetFlow – Analytics Dashboard View.

Computes all KPIs at query time using aggregation + supplies
Chart.js-compatible JSON data for visual charts on the dashboard.

Charts provided:
1. Vehicle Status Breakdown (Doughnut)
2. Trip Status Breakdown (Doughnut)
3. Monthly Trips Trend – last 6 months (Bar)
4. Expense by Category (Bar)
5. Monthly Revenue vs Expenses (Line)
"""
import json
from datetime import date

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.fleet.models import Vehicle
from apps.dispatch.models import Driver, Trip
from apps.maintenance.models import MaintenanceLog
from apps.finance.models import Expense, Invoice


class DashboardView(LoginRequiredMixin, View):
    """
    Main analytics dashboard with live KPI cards and Chart.js charts.
    Accessible to all authenticated users (read-only).
    """
    template_name = "analytics/dashboard.html"

    def get(self, request):
        today = timezone.now().date()

        # ── Fleet KPIs ────────────────────────────────────────────────────────
        vehicles = Vehicle.objects.all()
        total_vehicles = vehicles.count()
        available_vehicles = vehicles.filter(status=Vehicle.Status.AVAILABLE).count()
        on_trip_vehicles = vehicles.filter(status=Vehicle.Status.ON_TRIP).count()
        in_maintenance_vehicles = vehicles.filter(status=Vehicle.Status.IN_MAINTENANCE).count()
        decommissioned_vehicles = vehicles.filter(status=Vehicle.Status.DECOMMISSIONED).count()

        fleet_utilization = (
            round((on_trip_vehicles / total_vehicles) * 100, 1)
            if total_vehicles > 0 else 0
        )

        # ── Driver KPIs ───────────────────────────────────────────────────────
        total_drivers = Driver.objects.count()
        available_drivers = Driver.objects.filter(
            status=Driver.Status.AVAILABLE, is_suspended=False
        ).count()
        suspended_drivers = Driver.objects.filter(is_suspended=True).count()

        license_expiring_soon = Driver.objects.filter(
            license_expires_on__lte=today + timezone.timedelta(days=30),
            license_expires_on__gte=today,
        ).count()

        # ── Trip KPIs ─────────────────────────────────────────────────────────
        trips = Trip.objects.all()
        total_trips = trips.count()
        active_trips = trips.filter(
            status__in=[Trip.Status.DISPATCHED, Trip.Status.IN_TRANSIT]
        ).count()
        completed_trips = trips.filter(status=Trip.Status.COMPLETED).count()
        cancelled_trips = trips.filter(status=Trip.Status.CANCELLED).count()

        # ── Financial KPIs ────────────────────────────────────────────────────
        total_expenses = Expense.objects.aggregate(total=Sum("amount"))["total"] or 0
        total_revenue = Invoice.objects.filter(
            status=Invoice.Status.PAID
        ).aggregate(total=Sum("amount_charged"))["total"] or 0
        gross_profit = total_revenue - total_expenses

        # ── Maintenance ───────────────────────────────────────────────────────
        open_maintenance = MaintenanceLog.objects.filter(
            status__in=[MaintenanceLog.Status.OPEN, MaintenanceLog.Status.IN_PROGRESS]
        ).count()

        # ── Recent trips ──────────────────────────────────────────────────────
        recent_trips = Trip.objects.select_related(
            "created_by", "assignment__vehicle", "assignment__driver__user"
        ).order_by("-updated_at")[:10]

        # ═══════════════════════════════════════════════════════════════════════
        # CHART DATA (serialised to JSON for Chart.js)
        # ═══════════════════════════════════════════════════════════════════════

        # Chart 1: Vehicle Status Doughnut
        vehicle_status_chart = {
            "labels": ["Available", "On Trip", "In Maintenance", "Decommissioned"],
            "data": [available_vehicles, on_trip_vehicles, in_maintenance_vehicles, decommissioned_vehicles],
            "colors": ["#10b981", "#3b82f6", "#f59e0b", "#6b7280"],
        }

        # Chart 2: Trip Status Doughnut
        planned_trips = trips.filter(status=Trip.Status.PLANNED).count()
        trip_status_chart = {
            "labels": ["Planned", "Active", "Completed", "Cancelled"],
            "data": [planned_trips, active_trips, completed_trips, cancelled_trips],
            "colors": ["#8b5cf6", "#3b82f6", "#10b981", "#ef4444"],
        }

        # Chart 3: Monthly Trips (last 6 months) — Bar
        # Compute start of 6 months ago using plain Python
        from datetime import date as _date
        import calendar as _cal
        _now = today
        _y, _m = _now.year, _now.month
        _m -= 5
        if _m <= 0:
            _m += 12
            _y -= 1
        six_months_ago = _date(_y, _m, 1)

        monthly_trip_qs = (
            Trip.objects
            .filter(scheduled_at__date__gte=six_months_ago)
            .annotate(month=TruncMonth("scheduled_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        monthly_labels = [row["month"].strftime("%b %Y") for row in monthly_trip_qs]
        monthly_data = [row["count"] for row in monthly_trip_qs]
        monthly_trips_chart = {"labels": monthly_labels, "data": monthly_data}

        # Chart 4: Expense by Category — Bar
        expense_by_cat = (
            Expense.objects
            .values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        expense_cat_labels = [row["category"].title() for row in expense_by_cat]
        expense_cat_data = [float(row["total"] or 0) for row in expense_by_cat]
        expense_category_chart = {"labels": expense_cat_labels, "data": expense_cat_data}

        # Chart 5: Monthly Revenue vs Expenses (last 6 months) — Line
        monthly_revenue_qs = (
            Invoice.objects
            .filter(issued_at__gte=six_months_ago, status=Invoice.Status.PAID)
            .annotate(month=TruncMonth("issued_at"))
            .values("month")
            .annotate(total=Sum("amount_charged"))
            .order_by("month")
        )
        monthly_expense_qs = (
            Expense.objects
            .filter(date__gte=six_months_ago)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        rev_map = {row["month"].strftime("%b %Y"): float(row["total"] or 0) for row in monthly_revenue_qs}
        exp_map = {row["month"].strftime("%b %Y"): float(row["total"] or 0) for row in monthly_expense_qs}
        all_months_set = sorted(set(list(rev_map.keys()) + list(exp_map.keys())))
        revenue_expense_chart = {
            "labels": all_months_set,
            "revenue": [rev_map.get(m, 0) for m in all_months_set],
            "expenses": [exp_map.get(m, 0) for m in all_months_set],
        }

        context = {
            # Fleet
            "total_vehicles": total_vehicles,
            "available_vehicles": available_vehicles,
            "on_trip_vehicles": on_trip_vehicles,
            "in_maintenance_vehicles": in_maintenance_vehicles,
            "fleet_utilization": fleet_utilization,
            # Drivers
            "total_drivers": total_drivers,
            "available_drivers": available_drivers,
            "suspended_drivers": suspended_drivers,
            "license_expiring_soon": license_expiring_soon,
            # Trips
            "total_trips": total_trips,
            "active_trips": active_trips,
            "completed_trips": completed_trips,
            # Finance
            "total_expenses": total_expenses,
            "total_revenue": total_revenue,
            "gross_profit": gross_profit,
            # Maintenance
            "open_maintenance": open_maintenance,
            # Feed
            "recent_trips": recent_trips,
            # Chart JSON
            "vehicle_status_json": json.dumps(vehicle_status_chart),
            "trip_status_json": json.dumps(trip_status_chart),
            "monthly_trips_json": json.dumps(monthly_trips_chart),
            "expense_category_json": json.dumps(expense_category_chart),
            "revenue_expense_json": json.dumps(revenue_expense_chart),
        }
        return render(request, self.template_name, context)
