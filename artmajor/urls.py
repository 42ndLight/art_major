"""
URL configuration for artmajor project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from core.views import HealthView

urlpatterns = [
    # Root redirect
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),

    # Admin
    path("admin/", admin.site.urls),

    # Accounts (auth + profile)
    path("accounts/", include("accounts.urls")),

    # Dashboard + core
    path("dashboard/", include("core.urls")),

    # Settings / profile shortcut
    path("settings/", include("accounts.urls_settings")),

    # Customers & Projects
    path("customers/", include("customers.urls")),
    path("projects/", include("projects.urls")),

    # Billing (Invoices, Payments, Public Invoice & Receipts)
    path("", include("billing.urls")),

    # Health check (top-level, no auth)
    path("health/", HealthView.as_view(), name="health"),
]
