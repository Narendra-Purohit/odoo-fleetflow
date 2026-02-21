"""
FleetFlow – Finance App Views.

Fixes:
- InvoiceListView: annotate() eliminates N+1 (no per-row Python aggregation).
- Both list views use Paginator(25) to prevent memory issues at scale.
- ExpenseForm file receipt validated via forms.py clean_receipt().
- Financial Analyst role is now granted access via FINANCIAL_ANALYST_ROLES.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum

from apps.finance.models import Expense, Invoice
from apps.finance.forms import ExpenseForm, InvoiceForm
from apps.users.permissions import RoleRequiredMixin, MANAGER_ROLES, FINANCIAL_ANALYST_ROLES, ALL_ROLES

PAGE_SIZE = 25


class ExpenseListView(RoleRequiredMixin, View):
    template_name = "finance/expense_list.html"
    allowed_roles = ALL_ROLES  # any role can view expenses

    def get(self, request):
        expenses_qs = Expense.objects.select_related("trip", "vehicle", "added_by").order_by("-date")
        total = expenses_qs.aggregate(total=Sum("amount"))["total"] or 0

        paginator = Paginator(expenses_qs, PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, self.template_name, {
            "expenses": page_obj,
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
            "total": total,
        })


class ExpenseCreateView(RoleRequiredMixin, View):
    template_name = "finance/expense_form.html"
    allowed_roles = FINANCIAL_ANALYST_ROLES

    def get(self, request):
        return render(request, self.template_name, {"form": ExpenseForm()})

    def post(self, request):
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.added_by = request.user
            expense.save()
            messages.success(request, "Expense recorded.")
            return redirect("finance:expense_list")
        return render(request, self.template_name, {"form": form})


class InvoiceListView(RoleRequiredMixin, View):
    template_name = "finance/invoice_list.html"
    allowed_roles = ALL_ROLES  # any role can view invoices

    def get(self, request):
        # annotate() computes expense_total in a single JOIN query — no N+1
        invoices_qs = (
            Invoice.objects
            .select_related("trip")
            .annotate(expense_total=Sum("trip__expenses__amount"))
            .order_by("-issued_at")
        )
        paginator = Paginator(invoices_qs, PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))

        return render(request, self.template_name, {
            "invoices": page_obj,
            "page_obj": page_obj,
            "is_paginated": paginator.num_pages > 1,
        })


class InvoiceCreateView(RoleRequiredMixin, View):
    template_name = "finance/invoice_form.html"
    allowed_roles = FINANCIAL_ANALYST_ROLES

    def get(self, request):
        return render(request, self.template_name, {"form": InvoiceForm()})

    def post(self, request):
        form = InvoiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Invoice created.")
            return redirect("finance:invoice_list")
        return render(request, self.template_name, {"form": form})
