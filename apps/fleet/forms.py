"""
FleetFlow – Fleet App Forms.

Includes file upload security: MIME-type and extension validation
on VehicleDocumentForm to prevent arbitrary file uploads.
"""
import os
from django import forms
from apps.fleet.models import Vehicle, VehicleDocument, FuelLog

ALLOWED_DOC_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".heic"}
ALLOWED_DOC_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/heic"}

ALLOWED_RECEIPT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_RECEIPT_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def _validate_file_upload(file, allowed_extensions, allowed_mime_types, max_mb=5):
    """
    Reusable upload validator.

    Checks:
    - File extension is in the allowed set.
    - Content-type header is in the allowed set.
    - File size does not exceed max_mb megabytes.
    """
    if file is None:
        return file
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise forms.ValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed_extensions))}."
        )
    mime = getattr(file, "content_type", "")
    if mime and mime not in allowed_mime_types:
        raise forms.ValidationError(
            f"Unsupported MIME type '{mime}'. Please upload a PDF or image file."
        )
    max_bytes = max_mb * 1024 * 1024
    if file.size > max_bytes:
        raise forms.ValidationError(
            f"File too large. Maximum allowed size is {max_mb} MB."
        )
    return file


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "plate_number", "make", "model", "year", "color",
            "vin", "fuel_type", "max_capacity_kg", "odometer_km",
            "acquisition_cost", "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "acquisition_cost": forms.NumberInput(attrs={"step": "0.01", "placeholder": "e.g. 1500000"}),
        }
        labels = {
            "acquisition_cost": "Acquisition Cost (₹)",
        }
        help_texts = {
            "acquisition_cost": "Enter the purchase or lease cost. Required for ROI calculations.",
        }


class VehicleDocumentForm(forms.ModelForm):
    class Meta:
        model = VehicleDocument
        fields = ["doc_type", "document_number", "issued_on", "expires_on", "file", "notes"]
        widgets = {
            "issued_on": forms.DateInput(attrs={"type": "date"}),
            "expires_on": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_file(self):
        """Validate file extension, MIME type, and size for security."""
        return _validate_file_upload(
            self.cleaned_data.get("file"),
            ALLOWED_DOC_EXTENSIONS,
            ALLOWED_DOC_MIME_TYPES,
        )


class FuelLogForm(forms.ModelForm):
    class Meta:
        model = FuelLog
        fields = ["vehicle", "date", "liters", "cost_per_liter", "odometer_at_fill", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
