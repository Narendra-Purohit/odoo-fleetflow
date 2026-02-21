"""FleetFlow – Django Admin registrations for all apps."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import CustomUser, Role, UserProfile, PasswordResetOTP
from apps.fleet.models import Vehicle, VehicleDocument, FuelLog
from apps.dispatch.models import Driver, Trip, TripAssignment, Cargo
from apps.maintenance.models import MaintenanceLog, MaintenanceSchedule
from apps.finance.models import Expense, Invoice


# ── Users ─────────────────────────────────────────────────────────────────────

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ["email", "username", "role", "is_active", "is_staff"]
    list_display_links = ["email", "username"]  # needed when using list_editable
    list_filter = ["role", "is_active", "is_staff"]
    list_editable = ["is_active"]
    ordering = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "role")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "username", "password1", "password2", "role")}),
    )
    search_fields = ["email", "username"]

    def has_delete_permission(self, request, obj=None):
        # Superusers can delete anyone; staff can delete non-superusers
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ["user", "otp", "created_at", "is_used"]
    list_filter = ["is_used"]
    readonly_fields = ["otp", "created_at"]
    search_fields = ["user__email"]



@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "department"]


# ── Fleet ─────────────────────────────────────────────────────────────────────

class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "make", "model", "year", "status", "max_capacity_kg", "fuel_type"]
    list_filter = ["status", "fuel_type"]
    search_fields = ["plate_number", "make", "model"]
    inlines = [VehicleDocumentInline]


@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display = ["vehicle", "date", "liters", "cost_per_liter", "odometer_at_fill"]
    list_filter = ["vehicle"]


# ── Dispatch ──────────────────────────────────────────────────────────────────

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ["user", "license_number", "license_expires_on", "status", "is_suspended"]
    list_filter = ["status", "is_suspended"]
    search_fields = ["license_number", "user__email"]


class CargoInline(admin.TabularInline):
    model = Cargo
    extra = 0


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["trip_number", "origin", "destination", "status", "scheduled_at", "created_by"]
    list_filter = ["status"]
    search_fields = ["trip_number", "origin", "destination"]
    inlines = [CargoInline]
    readonly_fields = ["trip_number"]


@admin.register(TripAssignment)
class TripAssignmentAdmin(admin.ModelAdmin):
    list_display = ["trip", "vehicle", "driver", "assigned_at", "assigned_by"]


# ── Maintenance ───────────────────────────────────────────────────────────────

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ["vehicle", "service_type", "status", "start_date", "end_date", "cost"]
    list_filter = ["status", "service_type"]


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ["vehicle", "service_type", "next_due_at", "is_active"]


# ── Finance ───────────────────────────────────────────────────────────────────

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["category", "amount", "date", "trip", "vehicle", "added_by"]
    list_filter = ["category"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["trip", "client_name", "amount_charged", "status", "issued_at"]
    list_filter = ["status"]
