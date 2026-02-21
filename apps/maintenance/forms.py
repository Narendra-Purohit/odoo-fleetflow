"""
FleetFlow – Maintenance App Forms.
"""
from django import forms
from apps.maintenance.models import MaintenanceLog, MaintenanceSchedule


class MaintenanceLogForm(forms.ModelForm):
    class Meta:
        model = MaintenanceLog
        fields = [
            "vehicle", "service_type", "description",
            "start_date", "end_date", "cost", "vendor", "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class MaintenanceScheduleForm(forms.ModelForm):
    class Meta:
        model = MaintenanceSchedule
        fields = [
            "vehicle", "service_type", "interval_type",
            "interval_km", "interval_days",
            "last_done_at", "next_due_at", "notes",
        ]
        widgets = {
            "last_done_at": forms.DateInput(attrs={"type": "date"}),
            "next_due_at": forms.DateInput(attrs={"type": "date"}),
        }
