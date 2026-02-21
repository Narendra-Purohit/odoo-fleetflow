"""
FleetFlow – Fleet App Views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator

from apps.fleet.models import Vehicle, VehicleDocument, FuelLog
from apps.fleet.forms import VehicleForm, VehicleDocumentForm, FuelLogForm
from apps.users.permissions import RoleRequiredMixin, MANAGER_ROLES, DISPATCHER_ROLES, ALL_ROLES


PAGE_SIZE = 25


class VehicleListView(RoleRequiredMixin, View):
    template_name = "fleet/vehicle_list.html"
    allowed_roles = ALL_ROLES  # all roles can view the fleet

    def get(self, request):
        status_filter = request.GET.get("status", "")
        vehicles_qs = Vehicle.objects.all()
        if status_filter:
            vehicles_qs = vehicles_qs.filter(status=status_filter)

        paginator = Paginator(vehicles_qs, PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, self.template_name, {
            "vehicles": page_obj,
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
            "status_choices": Vehicle.Status.choices,
            "current_status": status_filter,
        })


class VehicleDetailView(RoleRequiredMixin, View):
    template_name = "fleet/vehicle_detail.html"
    allowed_roles = ALL_ROLES  # all roles can view vehicle details

    def get(self, request, pk):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        docs = vehicle.documents.all()
        fuel_logs = vehicle.fuel_logs.all()[:10]
        maint_logs = vehicle.maintenance_logs.all()[:5]
        return render(request, self.template_name, {
            "vehicle": vehicle,
            "docs": docs,
            "fuel_logs": fuel_logs,
            "maint_logs": maint_logs,
        })


class VehicleCreateView(RoleRequiredMixin, View):
    template_name = "fleet/vehicle_form.html"
    allowed_roles = MANAGER_ROLES

    def get(self, request):
        return render(request, self.template_name, {"form": VehicleForm(), "action": "Add"})

    def post(self, request):
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.created_by = request.user
            vehicle.save()
            messages.success(request, f"Vehicle '{vehicle.plate_number}' added.")
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
        return render(request, self.template_name, {"form": form, "action": "Add"})


class VehicleUpdateView(RoleRequiredMixin, View):
    template_name = "fleet/vehicle_form.html"
    allowed_roles = MANAGER_ROLES

    def get(self, request, pk):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        return render(request, self.template_name, {"form": VehicleForm(instance=vehicle), "action": "Edit"})

    def post(self, request, pk):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Vehicle '{vehicle.plate_number}' updated.")
            return redirect("fleet:vehicle_detail", pk=vehicle.pk)
        return render(request, self.template_name, {"form": form, "action": "Edit"})


class FuelLogCreateView(RoleRequiredMixin, View):
    template_name = "fleet/fuel_log_form.html"
    allowed_roles = ALL_ROLES  # any authenticated user can log fuel

    def get(self, request):
        return render(request, self.template_name, {"form": FuelLogForm()})

    def post(self, request):
        form = FuelLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.logged_by = request.user
            log.save()
            messages.success(request, "Fuel log recorded.")
            return redirect("fleet:vehicle_detail", pk=log.vehicle_id)
        return render(request, self.template_name, {"form": form})
