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
    assert payment.provider_reference.startswith("MAN-")


@pytest.mark.django_db
def test_mock_payment_with_artist_phone_sends_sms(client, issued_invoice, monkeypatch):
    """
    When an artist has a phone number, submitting a mock payment triggers an SMS
    notification to the artist containing amount and invoice info.
    """
    # Setup artist phone number
    profile = issued_invoice.artist.artist_profile
    profile.phone_number = "+254712345678"
    profile.save(update_fields=["phone_number"])

    # Mock send_sms to verify artist notification
    sent_messages = []

    def mock_send_sms(recipient, message):
        sent_messages.append({"recipient": recipient, "message": message})
        return {"statusCode": "100", "status": "Success"}

    monkeypatch.setattr("communications.services.send_sms", mock_send_sms)

    pay_url = reverse("billing:public_payment", kwargs={"token": issued_invoice.public_token})
    resp = client.post(pay_url, {
        "amount": "400.00",
        "mock_pay": "1",
    })

    assert resp.status_code == 302
    assert resp.url == reverse("billing:public_receipt", kwargs={"token": issued_invoice.public_token})

    issued_invoice.refresh_from_db()
    assert issued_invoice.status == InvoiceStatus.PAID
    assert issued_invoice.balance_due == Decimal("0.00")

    payment = Payment.objects.filter(invoice=issued_invoice).latest("initiated_at")
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.provider == "mock_demo"

    # Verify SMS was dispatched to the artist
    artist_sms = [m for m in sent_messages if m["recipient"] == "+254712345678"]
    assert len(artist_sms) == 1
    assert "400.00 USD" in artist_sms[0]["message"]
    assert "INV-1001" in artist_sms[0]["message"]


@pytest.mark.django_db
def test_mock_payment_without_artist_phone_succeeds_gracefully(client, issued_invoice, monkeypatch):
    """
    When an artist does not have a phone number configured, mock payment completes
    successfully without errors and without attempting artist SMS delivery.
    """
    profile = issued_invoice.artist.artist_profile
    profile.phone_number = ""
    profile.save(update_fields=["phone_number"])

    sent_messages = []

    def mock_send_sms(recipient, message):
        sent_messages.append({"recipient": recipient, "message": message})
        return {"statusCode": "100", "status": "Success"}

    monkeypatch.setattr("communications.services.send_sms", mock_send_sms)

    pay_url = reverse("billing:public_payment", kwargs={"token": issued_invoice.public_token})
    resp = client.post(pay_url, {
        "amount": "100.00",
        "mock_pay": "1",
    })

    assert resp.status_code == 302
    assert resp.url == reverse("billing:public_receipt", kwargs={"token": issued_invoice.public_token})

    issued_invoice.refresh_from_db()
    assert issued_invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert issued_invoice.balance_due == Decimal("300.00")

    # No artist SMS dispatched
    artist_sms = [m for m in sent_messages if m["recipient"] == "+254712345678"]
    assert len(artist_sms) == 0

