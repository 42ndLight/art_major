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
