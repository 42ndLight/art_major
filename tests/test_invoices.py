"""
Tests for Invoice draft creation, server calculations, issuing, and voiding.
"""
from decimal import Decimal
import pytest
from django.urls import reverse

from billing.models import Invoice, InvoiceLine, InvoiceStatus
from customers.models import Customer
from projects.models import Project


@pytest.mark.django_db
def test_create_invoice_draft_and_server_calculation(auth_client, artist_user):
    customer = Customer.objects.create(artist=artist_user, name="Art Collector")
    project = Project.objects.create(artist=artist_user, customer=customer, title="Sculpture 1")

    url = reverse("billing:invoice_create")
    post_data = {
        "customer": str(customer.pk),
        "project": str(project.pk),
        "invoice_number": "INV-0001",
        "currency": "USD",
        "issue_date": "2026-10-28",
        "discount_amount": "50.00",
        "notes": "Net 14 days",
        # Formset management
        "lines-TOTAL_FORMS": "2",
        "lines-INITIAL_FORMS": "0",
        "lines-MIN_NUM_FORMS": "1",
        "lines-MAX_NUM_FORMS": "1000",
        # Line 0
        "lines-0-description": "Concept sketches",
        "lines-0-quantity": "2.00",
        "lines-0-unit_price": "200.00",
        # Line 1
        "lines-1-description": "3D Sculpting",
        "lines-1-quantity": "1.00",
        "lines-1-unit_price": "650.00",
    }
    response = auth_client.post(url, post_data)
    assert response.status_code == 302

    invoice = Invoice.objects.get(invoice_number="INV-0001")
    assert invoice.artist == artist_user
    assert invoice.status == InvoiceStatus.DRAFT
    assert invoice.lines.count() == 2

    # Check server-calculated totals:
    # Line 0: 2 * 200 = 400.00
    # Line 1: 1 * 650 = 650.00
    # Subtotal: 1050.00
    # Total: 1050 - 50 discount = 1000.00
    assert invoice.subtotal == Decimal("1050.00")
    assert invoice.total_amount == Decimal("1000.00")
    assert invoice.balance_due == Decimal("1000.00")


@pytest.mark.django_db
def test_issue_and_void_invoice_lifecycle(auth_client, artist_user):
    customer = Customer.objects.create(artist=artist_user, name="Patron")
    invoice = Invoice.objects.create(
        artist=artist_user,
        customer=customer,
        invoice_number="INV-0002",
        currency="USD",
        status=InvoiceStatus.DRAFT,
    )
    InvoiceLine.objects.create(
        invoice=invoice,
        description="Cover design",
        quantity=Decimal("1.00"),
        unit_price=Decimal("500.00"),
    )
    invoice.calculate_totals()

    assert not invoice.public_token
    assert invoice.issued_at is None

    # Issue invoice
    issue_url = reverse("billing:invoice_issue", kwargs={"pk": invoice.pk})
    resp = auth_client.post(issue_url)
    assert resp.status_code == 302

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.ISSUED
    assert len(invoice.public_token) >= 32
    assert invoice.issued_at is not None

    # Void invoice
    void_url = reverse("billing:invoice_void", kwargs={"pk": invoice.pk})
    resp = auth_client.post(void_url)
    assert resp.status_code == 302

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.VOID
    assert invoice.voided_at is not None


@pytest.mark.django_db
def test_invoice_owner_scoping(client, artist_user, another_artist):
    other_customer = Customer.objects.create(artist=another_artist, name="Foreign Client")
    other_invoice = Invoice.objects.create(
        artist=another_artist,
        customer=other_customer,
        invoice_number="INV-9999",
    )

    client.login(username="artist@example.com", password="testpass123")

    # Detail 404
    assert client.get(reverse("billing:invoice_detail", kwargs={"pk": other_invoice.pk})).status_code == 404
    # Issue 404
    assert client.post(reverse("billing:invoice_issue", kwargs={"pk": other_invoice.pk})).status_code == 404
    # Void 404
    assert client.post(reverse("billing:invoice_void", kwargs={"pk": other_invoice.pk})).status_code == 404
