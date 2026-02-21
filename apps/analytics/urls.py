"""FleetFlow – analytics app URLs."""
from django.urls import path
from apps.analytics import views
from django.views.generic import RedirectView

app_name = "analytics"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("", RedirectView.as_view(pattern_name="analytics:dashboard"), name="root"),
]
