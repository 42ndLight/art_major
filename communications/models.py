import uuid

from django.conf import settings
from django.db import models


class InboundSMS(models.Model):
    """Minimal audit record for inbound commands; SMS text itself is not retained."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_message_id = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=64, unique=True)
    artist = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    sender = models.CharField(max_length=32)
    message_digest = models.CharField(max_length=64)
    command = models.CharField(max_length=20, blank=True)
    outcome = models.CharField(max_length=30, default="received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
