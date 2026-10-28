"""
Project/Commission models for Artist Business Workspace.
"""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from customers.models import Customer


class ProjectStatus(models.TextChoices):
    INQUIRY = "inquiry", "Inquiry"
    ACCEPTED = "accepted", "Accepted"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    ON_HOLD = "on_hold", "On Hold"
    CANCELLED = "cancelled", "Cancelled"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    agreed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, default="USD")
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.INQUIRY,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "project"
        verbose_name_plural = "projects"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["artist", "status"]),
            models.Index(fields=["artist", "customer"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.customer.name})"

    def clean(self):
        super().clean()
        if self.customer_id and self.artist_id:
            if self.customer.artist_id != self.artist_id:
                raise ValidationError({"customer": "The customer must belong to you."})

    def save(self, *args, **kwargs):
        if self.status == ProjectStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != ProjectStatus.COMPLETED and self.completed_at:
            self.completed_at = None
        super().save(*args, **kwargs)
