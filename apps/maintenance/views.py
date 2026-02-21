"""
FleetFlow – Maintenance App Views.

All log creation/closing routes through MaintenanceService to ensure
@transaction.atomic wrapping — preventing partial state bugs.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator

from apps.maintenance.models import MaintenanceLog, MaintenanceSchedule
from apps.maintenance.forms import MaintenanceLogForm, MaintenanceScheduleForm
from apps.maintenance.services import MaintenanceService
from apps.users.permissions import RoleRequiredMixin, SAFETY_ROLES, MANAGER_ROLES, ALL_ROLES

PAGE_SIZE = 25


class MaintenanceLogListView(RoleRequiredMixin, View):
    template_name = "maintenance/log_list.html"
    allowed_roles = ALL_ROLES  # any role can view maintenance logs

    def get(self, request):
        status_filter = request.GET.get("status", "")
        logs_qs = MaintenanceLog.objects.select_related("vehicle", "logged_by")
        if status_filter:
            logs_qs = logs_qs.filter(status=status_filter)

        paginator = Paginator(logs_qs, PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, self.template_name, {
            "logs": page_obj,
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
            "status_choices": MaintenanceLog.Status.choices,
            "current_status": status_filter,
        })


class MaintenanceLogCreateView(RoleRequiredMixin, View):
    template_name = "maintenance/log_form.html"
    allowed_roles = SAFETY_ROLES

    def get(self, request):
        return render(request, self.template_name, {"form": MaintenanceLogForm(), "action": "Add"})

    def post(self, request):
        form = MaintenanceLogForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                MaintenanceService.open_log(
                    vehicle=cd["vehicle"],
                    service_type=cd["service_type"],
                    description=cd["description"],
                    logged_by=request.user,
                    start_date=cd.get("start_date"),
                    vendor=cd.get("vendor", ""),
                    notes=cd.get("notes", ""),
                )
                messages.success(request, "Maintenance log created.")
                return redirect("maintenance:log_list")
            except Exception as exc:
                messages.error(request, str(exc))
        return render(request, self.template_name, {"form": form, "action": "Add"})


class MaintenanceLogUpdateView(RoleRequiredMixin, View):
    template_name = "maintenance/log_form.html"
    allowed_roles = SAFETY_ROLES

    def get(self, request, pk):
        log = get_object_or_404(MaintenanceLog, pk=pk)
        return render(request, self.template_name, {"form": MaintenanceLogForm(instance=log), "action": "Edit"})

    def post(self, request, pk):
        log = get_object_or_404(MaintenanceLog, pk=pk)
        form = MaintenanceLogForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, "Maintenance log updated.")
            return redirect("maintenance:log_list")
        return render(request, self.template_name, {"form": form, "action": "Edit"})


class CloseMaintenanceLogView(RoleRequiredMixin, View):
    """One-click close a maintenance log via MaintenanceService (atomic)."""
    allowed_roles = SAFETY_ROLES

    def post(self, request, pk):
        log = get_object_or_404(MaintenanceLog, pk=pk)
        cost_raw = request.POST.get("cost")
        cost = float(cost_raw) if cost_raw else None
        try:
            MaintenanceService.close_log(log, cost=cost)
            messages.success(
                request,
                f"Maintenance log closed. Vehicle '{log.vehicle.plate_number}' set to Available."
            )
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("maintenance:log_list")
