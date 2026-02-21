"""
FleetFlow – Dispatch App Views.

Provides:
- Driver CRUD
- Trip lifecycle: create → assign → dispatch → complete → cancel
- Calls TripService for all state transitions (never modifies models directly)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator

from apps.dispatch.models import Driver, Trip, Cargo
from apps.dispatch.forms import DriverForm, TripForm, TripAssignmentForm, CargoForm
from apps.dispatch.services import TripService
from apps.users.permissions import RoleRequiredMixin, MANAGER_ROLES, DISPATCHER_ROLES, ALL_ROLES


PAGE_SIZE = 25


# ── Driver views ─────────────────────────────────────────────────────────────

class DriverListView(RoleRequiredMixin, View):
    template_name = "dispatch/driver_list.html"
    allowed_roles = ALL_ROLES  # any role can view drivers

    def get(self, request):
        drivers_qs = Driver.objects.select_related("user").all()
        paginator = Paginator(drivers_qs, PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))
        return render(request, self.template_name, {
            "drivers": page_obj,
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
        })


class DriverCreateView(RoleRequiredMixin, View):
    template_name = "dispatch/driver_form.html"
    allowed_roles = MANAGER_ROLES

    def get(self, request):
        return render(request, self.template_name, {"form": DriverForm(), "action": "Add"})

    def post(self, request):
        form = DriverForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Driver added successfully.")
            return redirect("dispatch:driver_list")
        return render(request, self.template_name, {"form": form, "action": "Add"})


class DriverUpdateView(RoleRequiredMixin, View):
    template_name = "dispatch/driver_form.html"
    allowed_roles = MANAGER_ROLES

    def get(self, request, pk):
        driver = get_object_or_404(Driver, pk=pk)
        return render(request, self.template_name, {"form": DriverForm(instance=driver), "action": "Edit"})

    def post(self, request, pk):
        driver = get_object_or_404(Driver, pk=pk)
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            form.save()
            messages.success(request, "Driver updated.")
            return redirect("dispatch:driver_list")
        return render(request, self.template_name, {"form": form, "action": "Edit"})


class DriverSuspendView(RoleRequiredMixin, View):
    """Toggle driver suspension – Manager only."""
    allowed_roles = MANAGER_ROLES

    def post(self, request, pk):
        driver = get_object_or_404(Driver, pk=pk)
        driver.is_suspended = not driver.is_suspended
        driver.save(update_fields=["is_suspended", "updated_at"])
        action = "suspended" if driver.is_suspended else "reinstated"
        messages.warning(request, f"Driver '{driver}' {action}.")
        return redirect("dispatch:driver_list")


# ── Trip views ────────────────────────────────────────────────────────────────

class TripListView(RoleRequiredMixin, View):
    template_name = "dispatch/trip_list.html"
    allowed_roles = ALL_ROLES  # any role can view trips

    def get(self, request):
        status_filter = request.GET.get("status", "")
        trips_qs = Trip.objects.select_related("created_by").prefetch_related(
            "assignment__vehicle", "assignment__driver"
        )
        if status_filter:
            trips_qs = trips_qs.filter(status=status_filter)

        paginator = Paginator(trips_qs, PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, self.template_name, {
            "trips": page_obj,
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
            "status_choices": Trip.Status.choices,
            "current_status": status_filter,
        })


class TripDetailView(RoleRequiredMixin, View):
    template_name = "dispatch/trip_detail.html"
    allowed_roles = ALL_ROLES  # any role can view trip details

    def get(self, request, pk):
        trip = get_object_or_404(
            Trip.objects.select_related("created_by")
            .prefetch_related("cargo_items", "assignment__vehicle", "assignment__driver"),
            pk=pk,
        )
        cargo_form = CargoForm()
        assign_form = TripAssignmentForm()
        return render(request, self.template_name, {
            "trip": trip,
            "cargo_form": cargo_form,
            "assign_form": assign_form,
        })


class TripCreateView(RoleRequiredMixin, View):
    template_name = "dispatch/trip_form.html"
    allowed_roles = DISPATCHER_ROLES  # only dispatchers/managers can create trips

    def get(self, request):
        return render(request, self.template_name, {"form": TripForm(), "action": "Create"})

    def post(self, request):
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.created_by = request.user
            trip.save()
            messages.success(request, f"Trip '{trip.trip_number}' created.")
            return redirect("dispatch:trip_detail", pk=trip.pk)
        return render(request, self.template_name, {"form": form, "action": "Create"})


class TripAddCargoView(RoleRequiredMixin, View):
    """Add a cargo item to a trip."""
    allowed_roles = DISPATCHER_ROLES  # dispatchers/managers manage cargo

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk, status=Trip.Status.PLANNED)
        form = CargoForm(request.POST)
        if form.is_valid():
            cargo = form.save(commit=False)
            cargo.trip = trip
            cargo.save()
            messages.success(request, "Cargo item added.")
        else:
            messages.error(request, str(form.errors))
        return redirect("dispatch:trip_detail", pk=pk)


class TripAssignView(RoleRequiredMixin, View):
    """Assign vehicle + driver to a trip via TripService."""
    allowed_roles = DISPATCHER_ROLES  # dispatchers/managers assign trips

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        form = TripAssignmentForm(request.POST)
        if form.is_valid():
            try:
                TripService.assign_trip(
                    trip=trip,
                    vehicle_id=form.cleaned_data["vehicle"].pk,
                    driver_id=form.cleaned_data["driver"].pk,
                    assigned_by=request.user,
                )
                messages.success(request, "Trip assigned successfully.")
            except (ValidationError, ValueError) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, str(form.errors))
        return redirect("dispatch:trip_detail", pk=pk)


class TripDispatchView(RoleRequiredMixin, View):
    """Transition trip PLANNED → DISPATCHED."""
    allowed_roles = DISPATCHER_ROLES

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            TripService.dispatch_trip(trip, actor=request.user)
            messages.success(request, f"Trip '{trip.trip_number}' dispatched.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dispatch:trip_detail", pk=pk)


class TripInTransitView(RoleRequiredMixin, View):
    """Transition trip DISPATCHED → IN_TRANSIT."""
    allowed_roles = DISPATCHER_ROLES

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            TripService.mark_in_transit(trip, actor=request.user)
            messages.success(request, f"Trip '{trip.trip_number}' is now in transit.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dispatch:trip_detail", pk=pk)


class TripCompleteView(RoleRequiredMixin, View):
    """Transition trip IN_TRANSIT → COMPLETED."""
    allowed_roles = DISPATCHER_ROLES

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        odometer_raw = request.POST.get("final_odometer")
        final_odometer = float(odometer_raw) if odometer_raw else None
        try:
            TripService.complete_trip(trip, final_odometer=final_odometer, actor=request.user)
            messages.success(request, f"Trip '{trip.trip_number}' completed.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dispatch:trip_detail", pk=pk)


class TripCancelView(RoleRequiredMixin, View):
    """Cancel a trip."""
    allowed_roles = MANAGER_ROLES

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk)
        try:
            TripService.cancel_trip(trip, actor=request.user)
            messages.warning(request, f"Trip '{trip.trip_number}' cancelled.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("dispatch:trip_list")
