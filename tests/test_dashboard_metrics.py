"""
Tests for Dashboard aggregated metrics and isolation.
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from django.urls import reverse

from billing.models import Invoice, InvoiceLine, InvoiceStatus, Payment, PaymentStatus
from customers.models import Customer
from projects.models import Project, ProjectStatus


@pytest.mark.django_db
def test_dashboard_aggregates_real_metrics(auth_client, artist_user):
    customer = Customer.objects.create(artist=artist_user, name="VIP Collector")

    # 1. Active project
    Project.objects.create(
        artist=artist_user,
        customer=customer,
        title="Active Painting",
        status=ProjectStatus.IN_PROGRESS,
    )
    # Completed project (should not be counted in active projects)
    Project.objects.create(
        artist=artist_user,
        customer=customer,
        title="Finished Work",
        status=ProjectStatus.COMPLETED,
    )

    # 2. Issued invoice with balance due
    inv1 = Invoice.objects.create(
        artist=artist_user,
        customer=customer,
        invoice_number="INV-001",
        currency="USD",
        due_date=date.today() - timedelta(days=5),  # Overdue
    )
    InvoiceLine.objects.create(invoice=inv1, description="Art piece", quantity=1, unit_price=Decimal("500.00"))
    inv1.calculate_totals()
    inv1.issue()

    # 3. Partially paid invoice
    inv2 = Invoice.objects.create(
        artist=artist_user,
        customer=customer,
        invoice_number="INV-002",
        currency="USD",
        due_date=date.today() + timedelta(days=10),
    )
    InvoiceLine.objects.create(invoice=inv2, description="Print edition", quantity=1, unit_price=Decimal("300.00"))
    inv2.calculate_totals()
    inv2.issue()

    # Record 100 payment for inv2
    Payment.objects.create(
        artist=artist_user,
        invoice=inv2,
        amount=Decimal("100.00"),
        currency="USD",
        status=PaymentStatus.SUCCEEDED,
    )

    response = auth_client.get(reverse("dashboard"))
    assert response.status_code == 200
    content = response.content.decode()

    # Total outstanding = 500 (inv1) + 200 (inv2 balance) = 700.00
    assert "700.00 USD" in content
    # Confirmed payment = 100.00
    assert "100.00 USD" in content
    # 1 active project
    assert "Active commissions" in content
    # 1 overdue invoice
    assert "Overdue invoices" in content
