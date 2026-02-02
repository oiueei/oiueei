"""
URL configuration for OIUEEI project.
"""

from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("core.urls")),
    # DRF login for browsable API (development only)
    path("api-auth/", include("rest_framework.urls")),
]
