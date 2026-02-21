"""FleetFlow URL configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("apps.users.urls", namespace="users")),
    path("fleet/", include("apps.fleet.urls", namespace="fleet")),
    path("dispatch/", include("apps.dispatch.urls", namespace="dispatch")),
    path("maintenance/", include("apps.maintenance.urls", namespace="maintenance")),
    path("finance/", include("apps.finance.urls", namespace="finance")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
    # Root redirect → dashboard
    path("", RedirectView.as_view(url="/analytics/dashboard/"), name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
