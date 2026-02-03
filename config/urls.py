"""
URL configuration for OIUEEI project.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),
    # DRF login for browsable API (development only)
    path("api-auth/", include("rest_framework.urls")),
]
