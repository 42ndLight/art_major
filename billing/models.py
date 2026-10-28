"""
Billing models: Invoice, InvoiceLine, and Payment for Artist Business Workspace.
"""
from decimal import Decimal
import secrets
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from customers.models import Customer
from projects.models import Project


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ISSUED = "issued", "Issued"
    PARTIALLY_PAID = "partially_paid", "Partially Paid"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    VOID = "void", "Void"


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )
    currency = models.CharField(max_length=3, default="USD")
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    public_token = models.CharField(max_length=64, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "invoice"
        verbose_name_plural = "invoices"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["artist", "invoice_number"],
                name="unique_artist_invoice_number",
            )
        ]
        indexes = [
            models.Index(fields=["artist", "status"]),
            models.Index(fields=["public_token"]),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name} ({self.total_amount} {self.currency})"

    def clean(self):
        super().clean()
        if self.customer_id and self.artist_id:
            if self.customer.artist_id != self.artist_id:
                raise ValidationError({"customer": "The customer must belong to you."})
        if self.project_id and self.artist_id:
            if self.project.artist_id != self.artist_id:
                raise ValidationError({"project": "The project must belong to you."})
            if self.customer_id and self.project.customer_id != self.customer_id:
                raise ValidationError({"project": "The project must belong to the selected customer."})

    @property
    def amount_paid(self) -> Decimal:
        succeeded_payments = self.payments.filter(status=PaymentStatus.SUCCEEDED)
        total_paid = succeeded_payments.aggregate(total=models.Sum("amount"))["total"]
        return total_paid if total_paid is not None else Decimal("0.00")

    @property
    def balance_due(self) -> Decimal:
        balance = self.total_amount - self.amount_paid
        return max(Decimal("0.00"), balance)

    @property
    def is_overdue(self) -> bool:
        if self.status in [InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]:
            if self.due_date and self.due_date < timezone.now().date():
                return True
        return False

    def calculate_totals(self, save=True):
        lines = self.lines.all()
        subtotal = sum((line.line_total for line in lines), Decimal("0.00"))
        self.subtotal = subtotal
        self.total_amount = max(Decimal("0.00"), subtotal - (self.discount_amount or Decimal("0.00")))
        if save and self.pk:
            self.save(update_fields=["subtotal", "total_amount", "updated_at"])

    def issue(self):
        if not self.public_token:
            self.public_token = secrets.token_urlsafe(32)
        self.status = InvoiceStatus.ISSUED
        self.issued_at = timezone.now()
        self.save(update_fields=["public_token", "status", "issued_at", "updated_at"])

    def void(self):
        self.status = InvoiceStatus.VOID
        self.voided_at = timezone.now()
        self.save(update_fields=["status", "voided_at", "updated_at"])

    def update_payment_status(self):
        if self.status == InvoiceStatus.VOID:
            return
        paid = self.amount_paid
        if paid >= self.total_amount and self.total_amount > Decimal("0.00"):
            self.status = InvoiceStatus.PAID
        elif paid > Decimal("0.00"):
            self.status = InvoiceStatus.PARTIALLY_PAID
        elif self.status in [InvoiceStatus.PAID, InvoiceStatus.PARTIALLY_PAID]:
            self.status = InvoiceStatus.ISSUED
        self.save(update_fields=["status", "updated_at"])

    @classmethod
    def generate_next_number(cls, artist):
        count = cls.objects.filter(artist=artist).count() + 1
        return f"INV-{count:04d}"


class InvoiceLine(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "invoice line"
        verbose_name_plural = "invoice lines"
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.description} ({self.quantity} @ {self.unit_price})"

    def save(self, *args, **kwargs):
        self.line_total = (self.quantity or Decimal("0.00")) * (self.unit_price or Decimal("0.00"))
        super().save(*args, **kwargs)


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    provider = models.CharField(max_length=50, default="demo_stub")
    provider_reference = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.SUCCEEDED,
    )
    payment_method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    initiated_at = models.DateTimeField(default=timezone.now)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "payment"
        verbose_name_plural = "payments"
        ordering = ["-initiated_at"]
        indexes = [
            models.Index(fields=["artist", "status"]),
            models.Index(fields=["invoice", "status"]),
        ]

    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency} ({self.status})"

    def save(self, *args, **kwargs):
        if self.status == PaymentStatus.SUCCEEDED and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        super().save(*args, **kwargs)
        self.invoice.update_payment_status()
