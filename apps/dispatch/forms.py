"""
FleetFlow – Dispatch App Forms.
"""
from django import forms
from apps.dispatch.models import Driver, Trip, TripAssignment, Cargo


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            "user", "license_number", "license_expires_on",
            "license_class", "phone", "experience_years", "notes",
        ]
        widgets = {
            "license_expires_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ["origin", "destination", "scheduled_at", "distance_km", "notes"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class TripAssignmentForm(forms.Form):
    """
    Used in the trip assignment workflow.
    Only shows AVAILABLE vehicles and eligible drivers.
    """
    from apps.fleet.models import Vehicle

    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE),
        label="Vehicle",
        help_text="Only available vehicles are shown.",
    )
    driver = forms.ModelChoiceField(
        queryset=Driver.objects.filter(
            status=Driver.Status.AVAILABLE,
            is_suspended=False,
        ),
        label="Driver",
        help_text="Only available, non-suspended drivers are shown.",
    )


class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = ["description", "weight_kg", "volume_m3", "quantity", "is_hazardous", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
