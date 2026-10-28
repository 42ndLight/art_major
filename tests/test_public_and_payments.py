"""
Tests for Public Customer Invoice view, Demo Payment flow, and Receipts.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from billing.models import Invoice, InvoiceLine, InvoiceStatus, Payment, PaymentStatus
from customers.models import Customer


@pytest.fixture
def issued_invoice(db, artist_user):
    customer = Customer.objects.create(
        artist=artist_user,
        name="John Public",
        email="john@public.com",
    )
    invoice = Invoice.objects.create(
        artist=artist_user,
        customer=customer,
        invoice_number="INV-1001",
        currency="USD",
        notes="Please wire payment within 7 business days.",
    )
    InvoiceLine.objects.create(
        invoice=invoice,
        description="Character Design Commission",
        quantity=Decimal("1.00"),
        unit_price=Decimal("400.00"),
    )
    invoice.calculate_totals()
    invoice.issue()
    return invoice


@pytest.mark.django_db
def test_public_customer_can_view_invoice_without_login(client, issued_invoice):
    url = reverse(
        "billing:public_invoice", kwargs={"token": issued_invoice.public_token}
    )
    response = client.get(url)
    assert response.status_code == 200

    content = response.content.decode()
    assert "INV-1001" in content
    assert "Character Design Commission" in content
    assert "400.00 USD" in content
    assert "John Public" in content

    # Crucial security check: Public view does NOT leak artist private dashboard or management controls
    assert "Sign out" not in content
    assert "Edit Draft" not in content
    assert "Record Payment" not in content
    assert "dashboard" not in content.lower() or 'href="/dashboard/"' not in content


@pytest.mark.django_db
def test_draft_and_void_invoices_are_not_accessible_publicly(client, issued_invoice):
    # Void the invoice
    issued_invoice.void()

    url = reverse(
        "billing:public_invoice", kwargs={"token": issued_invoice.public_token}
    )
    response = client.get(url)
    assert response.status_code == 404
    assert "Invoice Unavailable" in response.content.decode()


@pytest.mark.django_db
def test_public_demo_payment_flow_and_receipt(client, issued_invoice):
    token = issued_invoice.public_token

    # 1. Customer opens payment page
    pay_url = reverse("billing:public_payment", kwargs={"token": token})
    resp = client.get(pay_url)
    assert resp.status_code == 200
    assert "Demo Sandbox Stub" in resp.content.decode()

    # 2. Customer submits a partial payment of $150
    post_data = {
        "amount": "150.00",
        "payment_method": "Credit Card (Sandbox Demo)",
    }
    pay_resp = client.post(pay_url, post_data)
    assert pay_resp.status_code == 302
    assert pay_resp.url == reverse("billing:public_receipt", kwargs={"token": token})

    issued_invoice.refresh_from_db()
    assert issued_invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert issued_invoice.amount_paid == Decimal("150.00")
    assert issued_invoice.balance_due == Decimal("250.00")

    # 3. Check public receipt view
    receipt_url = reverse("billing:public_receipt", kwargs={"token": token})
    receipt_resp = client.get(receipt_url)
    assert receipt_resp.status_code == 200
    assert "Payment Confirmed" in receipt_resp.content.decode()
    assert "150.00 USD" in receipt_resp.content.decode()

    # 4. Pay the remaining $250
    client.post(
        pay_url, {"amount": "250.00", "payment_method": "M-Pesa (Demo Simulator)"}
    )
    issued_invoice.refresh_from_db()
    assert issued_invoice.status == InvoiceStatus.PAID
    assert issued_invoice.amount_paid == Decimal("400.00")
    assert issued_invoice.balance_due == Decimal("0.00")


@pytest.mark.django_db
def test_artist_manual_payment_entry(auth_client, issued_invoice):
    url = reverse("billing:invoice_record_payment", kwargs={"pk": issued_invoice.pk})
    data = {
        "amount": "400.00",
        "payment_method": "Direct Bank Wire",
        "notes": "Verified in account",
    }
    resp = auth_client.post(url, data)
    assert resp.status_code == 302

    issued_invoice.refresh_from_db()
    assert issued_invoice.status == InvoiceStatus.PAID
    assert issued_invoice.amount_paid == Decimal("400.00")

    payment = Payment.objects.get(invoice=issued_invoice)
    assert payment.provider == "manual"
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.payment_method == "Direct Bank Wire"
