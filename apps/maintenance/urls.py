"""FleetFlow – maintenance app URLs."""
from django.urls import path
from apps.maintenance import views

app_name = "maintenance"

urlpatterns = [
    path("logs/", views.MaintenanceLogListView.as_view(), name="log_list"),
    path("logs/add/", views.MaintenanceLogCreateView.as_view(), name="log_create"),
    path("logs/<int:pk>/edit/", views.MaintenanceLogUpdateView.as_view(), name="log_update"),
    path("logs/<int:pk>/close/", views.CloseMaintenanceLogView.as_view(), name="log_close"),
]
