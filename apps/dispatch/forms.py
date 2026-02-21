"""
FleetFlow – Dispatch App Forms.
"""
from django import forms
from django.contrib.auth import get_user_model
from apps.dispatch.models import Driver, Trip, TripAssignment, Cargo

User = get_user_model()


class UserChoiceField(forms.ModelChoiceField):
    """Shows 'Full Name – email@example.com' in the driver user dropdown."""

    def label_from_instance(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        if full_name:
            return f"{full_name} – {obj.email}"
        return obj.email


class DriverForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # For existing driver (edit), allow current user + unassigned users.
        # For new driver, only show users without an existing driver profile.
        existing_driver_user_ids = Driver.objects.values_list("user_id", flat=True)
        if self.instance and self.instance.pk:
            available_users = User.objects.exclude(
                driver_profile__isnull=False
            ).exclude(pk=self.instance.user_id) | User.objects.filter(pk=self.instance.user_id)
        else:
            available_users = User.objects.exclude(id__in=existing_driver_user_ids)
        self.fields["user"].queryset = available_users.order_by("first_name", "last_name", "email")

    class Meta:
        model = Driver
        fields = [
            "user", "license_number", "license_expires_on",
            "license_class", "phone", "experience_years", "notes",
        ]
        field_classes = {
            "user": UserChoiceField,
        }
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
