"""
URL patterns for settings-scoped routes (e.g. /settings/profile/).
"""
from django.urls import path

from .views import ProfileView

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
]
