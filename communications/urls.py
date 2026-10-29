from django.urls import path

from .views import inbound_sms

urlpatterns = [
    path("webhooks/africastalking/inbound/", inbound_sms, name="africastalking-inbound"),
    path("webhooks/africastalking/inbound/<str:token>/", inbound_sms, name="africastalking-inbound-token"),
]
