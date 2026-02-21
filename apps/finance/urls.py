"""FleetFlow – finance app URLs."""
from django.urls import path
from apps.finance import views

app_name = "finance"

urlpatterns = [
    path("expenses/", views.ExpenseListView.as_view(), name="expense_list"),
    path("expenses/add/", views.ExpenseCreateView.as_view(), name="expense_create"),
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/create/", views.InvoiceCreateView.as_view(), name="invoice_create"),
]
