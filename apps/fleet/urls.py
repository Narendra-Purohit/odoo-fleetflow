"""FleetFlow – fleet app URLs."""
from django.urls import path
from apps.fleet import views

app_name = "fleet"

urlpatterns = [
    path("vehicles/", views.VehicleListView.as_view(), name="vehicle_list"),
    path("vehicles/add/", views.VehicleCreateView.as_view(), name="vehicle_create"),
    path("vehicles/<int:pk>/", views.VehicleDetailView.as_view(), name="vehicle_detail"),
    path("vehicles/<int:pk>/edit/", views.VehicleUpdateView.as_view(), name="vehicle_update"),
    path("fuel-logs/add/", views.FuelLogCreateView.as_view(), name="fuel_log_create"),
]
