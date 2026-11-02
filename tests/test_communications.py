"""
Tests for Africa's Talking inbound SMS webhook and SMS command execution.
"""
from django.utils import timezone
import pytest
from django.urls import reverse

from customers.models import Customer
from communications.models import InboundSMS


@pytest.fixture
def verified_artist(artist_user):
    profile = artist_user.artist_profile
    profile.phone_number = "+254712345678"
    profile.phone_verified_at = timezone.now()
    profile.save(update_fields=["phone_number", "phone_verified_at"])
    return artist_user


@pytest.mark.django_db
def test_inbound_sms_open_endpoint_recognized_artist(client, verified_artist, monkeypatch):
    """
    POST to open inbound endpoint without token executes commands for recognized artist.
    """
    sent_replies = []

    def mock_send_sms(recipient, message):
        sent_replies.append({"recipient": recipient, "message": message})
        return {"statusCode": "100", "status": "Success"}

    monkeypatch.setattr("communications.views.send_sms", mock_send_sms)

    payload = {
        "from": "+254712345678",
        "text": "CUSTOMER|Alice Walker|+254700112233",
        "id": "AT_MSG_001",
    }

    url = reverse("africastalking-inbound")
    response = client.post(url, payload)

    assert response.status_code == 200
    assert response.content == b"OK"

    # Customer should be created for this artist
    customer = Customer.objects.filter(artist=verified_artist, name="Alice Walker").first()
    assert customer is not None
    assert customer.phone_number == "+254700112233"

    # Inbound SMS record saved
    sms_record = InboundSMS.objects.get(provider_message_id="AT_MSG_001")
    assert sms_record.artist == verified_artist
    assert sms_record.outcome == "customer_created"

    # Reply SMS sent
    assert len(sent_replies) == 1
    assert sent_replies[0]["recipient"] == "+254712345678"
    assert "Customer Alice Walker created" in sent_replies[0]["message"]


@pytest.mark.django_db
def test_inbound_sms_legacy_token_route_supported(client, verified_artist, monkeypatch):
    """
    POST to legacy token endpoint `/webhooks/africastalking/inbound/<token>/` works without 404.
    """
    sent_replies = []

    def mock_send_sms(recipient, message):
        sent_replies.append({"recipient": recipient, "message": message})
        return {"statusCode": "100", "status": "Success"}

    monkeypatch.setattr("communications.views.send_sms", mock_send_sms)

    payload = {
        "from": "+254712345678",
        "text": "CUSTOMER|Bob Vance|+254700998877",
        "id": "AT_MSG_002",
    }

    url = reverse("africastalking-inbound-token", kwargs={"token": "legacy-token-123"})
    response = client.post(url, payload)

    assert response.status_code == 200
    assert response.content == b"OK"

    customer = Customer.objects.filter(artist=verified_artist, name="Bob Vance").first()
    assert customer is not None


@pytest.mark.django_db
def test_inbound_sms_unrecognized_sender_prompts_to_link(client, monkeypatch):
    """
    POST from unknown sender returns 200 OK with prompt to link account in profile settings.
    """
    sent_replies = []

    def mock_send_sms(recipient, message):
        sent_replies.append({"recipient": recipient, "message": message})
        return {"statusCode": "100", "status": "Success"}

    monkeypatch.setattr("communications.views.send_sms", mock_send_sms)

    payload = {
        "from": "+254799999999",
        "text": "CUSTOMER|Unknown Customer|+254700000000",
        "id": "AT_MSG_UNKNOWN_01",
    }

    url = reverse("africastalking-inbound")
    response = client.post(url, payload)

    assert response.status_code == 200
    assert response.content == b"OK"

    sms_record = InboundSMS.objects.get(provider_message_id="AT_MSG_UNKNOWN_01")
    assert sms_record.artist is None
    assert sms_record.outcome == "unrecognized_sender"

    assert len(sent_replies) == 1
    assert "not linked to a verified ArtMajor artist account" in sent_replies[0]["message"]


@pytest.mark.django_db
def test_inbound_sms_missing_required_fields_returns_400(client):
    """
    POST without required fields (from, text, id) returns 400 Bad Request.
    """
    url = reverse("africastalking-inbound")

    # Missing text
    resp = client.post(url, {"from": "+254712345678", "id": "MSG_001"})
    assert resp.status_code == 400

    # Missing from
    resp = client.post(url, {"text": "CUSTOMER|Test", "id": "MSG_002"})
    assert resp.status_code == 400

    # Missing id
    resp = client.post(url, {"from": "+254712345678", "text": "CUSTOMER|Test"})
    assert resp.status_code == 400


@pytest.mark.django_db
def test_inbound_sms_idempotency(client, verified_artist, monkeypatch):
    """
    Duplicate inbound message ID does not repeat command execution.
    """
    counter = {"calls": 0}

    def mock_send_sms(recipient, message):
        counter["calls"] += 1
        return {"statusCode": "100", "status": "Success"}

    monkeypatch.setattr("communications.views.send_sms", mock_send_sms)

    payload = {
        "from": "+254712345678",
        "text": "CUSTOMER|Duplicate Test|+254733445566",
        "id": "AT_MSG_DUP_001",
    }

    url = reverse("africastalking-inbound")
    resp1 = client.post(url, payload)
    assert resp1.status_code == 200

    assert counter["calls"] == 1
    assert Customer.objects.filter(artist=verified_artist, name="Duplicate Test").count() == 1

    # Second post with identical id
    resp2 = client.post(url, payload)
    assert resp2.status_code == 200

    # Should not re-send reply SMS or fail
    assert counter["calls"] == 1
    assert Customer.objects.filter(artist=verified_artist, name="Duplicate Test").count() == 1


@pytest.mark.django_db
def test_inbound_sms_updates_existing_customer_phone_and_details(client, verified_artist, monkeypatch):
    """Sending CUSTOMER command for an existing customer updates phone and email."""
    customer = Customer.objects.create(
        artist=verified_artist,
        name="Existing Client",
        phone_number="+254700000000",
    )

    sent_replies = []
    monkeypatch.setattr("communications.views.send_sms", lambda r, m: sent_replies.append({"recipient": r, "message": m}))

    # Update with new phone and email
    payload = {
        "from": "+254712345678",
        "text": "CUSTOMER|Existing Client|+254799887766|client@example.com",
        "id": "AT_MSG_UPDATE_001",
    }
    resp = client.post(reverse("africastalking-inbound"), payload)
    assert resp.status_code == 200

    customer.refresh_from_db()
    assert customer.phone_number == "+254799887766"
    assert customer.email == "client@example.com"

    sms_record = InboundSMS.objects.get(provider_message_id="AT_MSG_UPDATE_001")
    assert sms_record.outcome == "customer_updated"
    assert "updated" in sent_replies[0]["message"]


@pytest.mark.django_db
def test_inbound_sms_creates_and_updates_invoice_draft(client, verified_artist, monkeypatch):
    """
    INVOICE command creates a new draft for a customer, and INVOICE with the draft number
    updates the amount, currency, and line description.
    """
    customer = Customer.objects.create(
        artist=verified_artist,
        name="Bob Builder",
        phone_number="+254711223344",
    )

    sent_replies = []
    monkeypatch.setattr("communications.views.send_sms", lambda r, m: sent_replies.append({"recipient": r, "message": m}))

    # 1. Create new draft invoice with formatted amount (5,000)
    payload_create = {
        "from": "+254712345678",
        "text": "INVOICE|Bob Builder|5,000|KES|Site Blueprint Design",
        "id": "AT_MSG_INV_001",
    }
    resp1 = client.post(reverse("africastalking-inbound"), payload_create)
    assert resp1.status_code == 200

    from billing.models import Invoice, InvoiceStatus
    from decimal import Decimal

    invoice = Invoice.objects.filter(artist=verified_artist, customer=customer).first()
    assert invoice is not None
    assert invoice.status == InvoiceStatus.DRAFT
    assert invoice.total_amount == Decimal("5000.00")
    assert invoice.currency == "KES"
    assert invoice.lines.first().description == "Site Blueprint Design"

    # 2. Update existing draft invoice by its invoice number
    payload_update = {
        "from": "+254712345678",
        "text": f"INVOICE|{invoice.invoice_number}|6500|USD|Revised 3D Blueprint",
        "id": "AT_MSG_INV_002",
    }
    resp2 = client.post(reverse("africastalking-inbound"), payload_update)
    assert resp2.status_code == 200

    invoice.refresh_from_db()
    assert invoice.status == InvoiceStatus.DRAFT
    assert invoice.total_amount == Decimal("6500.00")
    assert invoice.currency == "USD"
    assert invoice.lines.first().description == "Revised 3D Blueprint"

    sms_record = InboundSMS.objects.get(provider_message_id="AT_MSG_INV_002")
    assert sms_record.outcome == "invoice_draft_updated"
    assert "updated" in sent_replies[-1]["message"]


@pytest.mark.django_db
def test_inbound_sms_cannot_update_non_draft_invoice(client, verified_artist, monkeypatch):
    """Attempting to update an issued invoice via SMS is rejected safely."""
    customer = Customer.objects.create(artist=verified_artist, name="Acme Corp")
    from billing.models import Invoice, InvoiceLine, InvoiceStatus
    from decimal import Decimal

    invoice = Invoice.objects.create(
        artist=verified_artist,
        customer=customer,
        invoice_number="INV-ISSUED-01",
        status=InvoiceStatus.ISSUED,
    )
    InvoiceLine.objects.create(invoice=invoice, description="Work", unit_price=Decimal("100.00"), quantity=Decimal("1.00"))
    invoice.calculate_totals()

    sent_replies = []
    monkeypatch.setattr("communications.views.send_sms", lambda r, m: sent_replies.append({"recipient": r, "message": m}))

    payload = {
        "from": "+254712345678",
        "text": "INVOICE|INV-ISSUED-01|200|USD|Tampered Work",
        "id": "AT_MSG_INV_003",
    }
    resp = client.post(reverse("africastalking-inbound"), payload)
    assert resp.status_code == 200

    invoice.refresh_from_db()
    assert invoice.total_amount == Decimal("100.00")  # Untouched

    sms_record = InboundSMS.objects.get(provider_message_id="AT_MSG_INV_003")
    assert sms_record.outcome == "invoice_immutable"
    assert "cannot be modified via SMS" in sent_replies[0]["message"]



def test_send_sms_accepts_standard_status_codes(monkeypatch, settings):
    """Africa's Talking status codes 100 (Processed), 101 (Sent), and 102 (Queued) must be treated as success."""
    import json
    from io import BytesIO
    from communications.services import send_sms

    settings.AFRICASTALKING_API_KEY = "dummy-key"
    settings.AFRICASTALKING_USERNAME = "sandbox"

    # Test 101 Sent (most common in real-world AT responses)
    class FakeResponse101:
        def read(self):
            return json.dumps({
                "SMSMessageData": {
                    "Message": "Sent to 1/1",
                    "Recipients": [{"statusCode": 101, "status": "Success", "number": "+254712345678", "cost": "KES 0.8"}]
                }
            }).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("communications.services.urlopen", lambda req, timeout=10: FakeResponse101())
    recipient_info = send_sms("+254712345678", "Test message")
    assert recipient_info["statusCode"] == 101
    assert recipient_info["status"] == "Success"

    # Test 100 Processed
    class FakeResponse100:
        def read(self):
            return json.dumps({
                "SMSMessageData": {
                    "Message": "Sent to 1/1",
                    "Recipients": [{"statusCode": 100, "status": "Processed", "number": "+254712345678"}]
                }
            }).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("communications.services.urlopen", lambda req, timeout=10: FakeResponse100())
    res100 = send_sms("+254712345678", "Test message")
    assert res100["statusCode"] == 100


def test_send_sms_raises_on_rejection(monkeypatch, settings):
    """send_sms raises AfricaTalkingError with details when provider rejects."""
    import json
    from communications.services import send_sms, AfricaTalkingError

    settings.AFRICASTALKING_API_KEY = "dummy-key"
    settings.AFRICASTALKING_USERNAME = "sandbox"

    class FakeResponse403:
        def read(self):
            return json.dumps({
                "SMSMessageData": {
                    "Message": "InvalidPhoneNumber",
                    "Recipients": [{"statusCode": 403, "status": "InvalidPhoneNumber", "number": "invalid"}]
                }
            }).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr("communications.services.urlopen", lambda req, timeout=10: FakeResponse403())
    with pytest.raises(AfricaTalkingError) as exc_info:
        send_sms("invalid", "Test message")
    assert "InvalidPhoneNumber" in str(exc_info.value)

