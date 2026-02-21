"""
FleetFlow – Finance App Forms.

ExpenseForm includes receipt file security:
- Extension whitelist: .pdf, .jpg, .jpeg, .png
- MIME type validation
- 5 MB size limit
"""
import os
from django import forms
from apps.finance.models import Expense, Invoice

ALLOWED_RECEIPT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_RECEIPT_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["trip", "vehicle", "category", "amount", "date", "receipt", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_receipt(self):
        """Validate uploaded receipt file extension, MIME type and size."""
        receipt = self.cleaned_data.get("receipt")
        if not receipt:
            return receipt
        ext = os.path.splitext(receipt.name)[1].lower()
        if ext not in ALLOWED_RECEIPT_EXTENSIONS:
            raise forms.ValidationError(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_RECEIPT_EXTENSIONS))}."
            )
        mime = getattr(receipt, "content_type", "")
        if mime and mime not in ALLOWED_RECEIPT_MIME_TYPES:
            raise forms.ValidationError(
                "Unsupported MIME type. Please upload a PDF or image file."
            )
        max_bytes = 5 * 1024 * 1024  # 5 MB
        if receipt.size > max_bytes:
            raise forms.ValidationError("Receipt file must not exceed 5 MB.")
        return receipt


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "trip", "client_name", "client_contact",
            "amount_charged", "status", "issued_at", "due_date", "notes",
        ]
        widgets = {
            "issued_at": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
