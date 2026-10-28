"""
URL patterns for the core app.
"""
from django.urls import path

from .views import DashboardView, HealthView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("health/", HealthView.as_view(), name="health-core"),
]
