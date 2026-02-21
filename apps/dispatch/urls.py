"""FleetFlow – dispatch app URLs."""
from django.urls import path
from apps.dispatch import views

app_name = "dispatch"

urlpatterns = [
    # Drivers
    path("drivers/", views.DriverListView.as_view(), name="driver_list"),
    path("drivers/add/", views.DriverCreateView.as_view(), name="driver_create"),
    path("drivers/<int:pk>/edit/", views.DriverUpdateView.as_view(), name="driver_update"),
    path("drivers/<int:pk>/suspend/", views.DriverSuspendView.as_view(), name="driver_suspend"),
    # Trips
    path("trips/", views.TripListView.as_view(), name="trip_list"),
    path("trips/create/", views.TripCreateView.as_view(), name="trip_create"),
    path("trips/<int:pk>/", views.TripDetailView.as_view(), name="trip_detail"),
    path("trips/<int:pk>/cargo/add/", views.TripAddCargoView.as_view(), name="trip_add_cargo"),
    path("trips/<int:pk>/assign/", views.TripAssignView.as_view(), name="trip_assign"),
    path("trips/<int:pk>/dispatch/", views.TripDispatchView.as_view(), name="trip_dispatch"),
    path("trips/<int:pk>/in-transit/", views.TripInTransitView.as_view(), name="trip_in_transit"),
    path("trips/<int:pk>/complete/", views.TripCompleteView.as_view(), name="trip_complete"),
    path("trips/<int:pk>/cancel/", views.TripCancelView.as_view(), name="trip_cancel"),
]
