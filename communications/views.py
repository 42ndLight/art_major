import hashlib
import json
import logging
import uuid
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from accounts.models import ArtistProfile
from .commands import parse_and_execute
from .models import InboundSMS
from .services import AfricaTalkingError, send_sms

logger = logging.getLogger(__name__)

# DEMO ONLY: in-memory record of outbound payment notifications.
# Keyed by "<artist_id>:<reference>". Resets on restart and is per-process.
OUTBOUND_PAYMENT_SMS = {}


@csrf_exempt
@require_POST
def inbound_sms(request, token=None):
    # Webhook endpoint is left open for Africa's Talking inbound SMS callbacks.
    # Authentication of actions is performed by verifying the sender's phone against active ArtistProfiles.
    data = request.POST
    if not data and request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return HttpResponse(status=400)
    sender = str(data.get("from", "")).strip()
    text = str(data.get("text", "")).strip()
    provider_id = str(data.get("id", "")).strip()[:120]
    if not sender or not text or len(text) > 1000 or not provider_id:
        return HttpResponse(status=400)

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    key_source = f"at:{provider_id}"
    key = hashlib.sha256(key_source.encode("utf-8")).hexdigest()
    with transaction.atomic():
        row, created = InboundSMS.objects.get_or_create(
            idempotency_key=key,
            defaults={"provider_message_id": provider_id, "sender": sender[:32], "message_digest": digest},
        )
        if not created:
            return HttpResponse("OK")

        profile = ArtistProfile.objects.select_related("user").filter(
            phone_number=sender,
            phone_verified_at__isnull=False,
            user__is_active=True,
        ).first()
        if profile:
            row.artist = profile.user
            reply, outcome = parse_and_execute(profile.user, text)
            row.command = text.split("|", 1)[0].strip().upper()[:20]
            row.outcome = outcome
        else:
            reply = "This number is not linked to a verified ArtMajor artist account. Link it in Settings > Profile first."
            row.outcome = "unrecognized_sender"
        row.save(update_fields=["artist", "command", "outcome"])
    try:
        send_sms(sender, reply[:480])
    except AfricaTalkingError:
        # Persist command success even if the provider is temporarily unavailable.
        pass
    return HttpResponse("OK")


def _read_payload(request):
    """Return form data or a JSON object body. Returns None if the body is invalid."""
    if request.POST:
        return request.POST
    if not request.body:
        return {}
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _mask_phone(phone):
    return f"{phone[:4]}***{phone[-3:]}" if len(phone) > 7 else "***"


@csrf_exempt
@require_POST
def payment_notification(request):
    """Send an SMS telling an artist a payment was received, and record the attempt.

    Sandbox demo: open like inbound_sms. Add authentication before production.
    Body (form or JSON): artist_id, amount, reference, currency (optional).
    """
    data = _read_payload(request)
    if data is None:
        return JsonResponse({"error": "Invalid request body."}, status=400)

    reference = str(data.get("reference", "")).strip()
    try:
        artist_id = uuid.UUID(str(data.get("artist_id", "")).strip())
        amount = Decimal(str(data.get("amount", "")).strip())
    except (ValueError, InvalidOperation):
        return JsonResponse({"error": "artist_id must be a UUID and amount a number."}, status=400)
    if not reference or len(reference) > 120 or not amount.is_finite() or amount <= 0:
        return JsonResponse({"error": "reference (max 120 chars) and a positive amount are required."}, status=400)

    profile = ArtistProfile.objects.filter(
        user_id=artist_id,
        phone_verified_at__isnull=False,
        user__is_active=True,
    ).first()
    if not profile:
        return JsonResponse({"error": "Artist not found or has no verified phone number."}, status=404)

    # Same artist + reference already notified: don't send twice.
    key = f"{artist_id}:{reference}"
    existing = OUTBOUND_PAYMENT_SMS.get(key)
    if existing and existing["status"] == "sent":
        return JsonResponse({**existing, "duplicate": True})

    currency = str(data.get("currency") or profile.default_currency).strip().upper()[:3]
    message = f"ArtMajor: Payment received! {amount:f} {currency} (ref {reference})."
    entry = {
        "artist_id": str(artist_id),
        "phone": _mask_phone(profile.phone_number),
        "reference": reference,
        "message": message,
        "status": "pending",
        "provider_message_id": "",
        "error": "",
        "created_at": timezone.now().isoformat(),
    }

    try:
        result = send_sms(profile.phone_number, message)
    except AfricaTalkingError as exc:
        entry.update(status="failed", error=str(exc))
        OUTBOUND_PAYMENT_SMS[key] = entry
        logger.warning("Payment SMS failed for artist %s ref %s: %s", artist_id, reference, exc)
        return JsonResponse(entry, status=502)

    entry.update(status="sent", provider_message_id=result.get("messageId", ""))
    OUTBOUND_PAYMENT_SMS[key] = entry
    logger.info("Payment SMS sent for artist %s ref %s", artist_id, reference)
    return JsonResponse(entry)


@require_GET
def payment_notification_log(request):
    """Demo helper: list recorded outbound payment notifications."""
    entries = list(OUTBOUND_PAYMENT_SMS.values())
    return JsonResponse({"count": len(entries), "entries": entries})
