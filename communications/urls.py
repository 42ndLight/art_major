from django.urls import path

from .views import inbound_sms, payment_notification, payment_notification_log

urlpatterns = [
    path("webhooks/africastalking/inbound/", inbound_sms, name="africastalking-inbound"),
    path("webhooks/africastalking/inbound/<str:token>/", inbound_sms, name="africastalking-inbound-token"),
    path("sms/payment-notification/", payment_notification, name="sms-payment-notification"),
    path("sms/payment-notifications/", payment_notification_log, name="sms-payment-notification-log"),
]