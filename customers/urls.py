"""
URL patterns for customers app.
"""
from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path("", views.CustomerListView.as_view(), name="list"),
    path("new/", views.CustomerCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.CustomerDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.CustomerUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/archive/", views.CustomerArchiveView.as_view(), name="archive"),
]
