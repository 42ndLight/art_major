import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import ArtistProfile
from .commands import parse_and_execute
from .models import InboundSMS
from .services import AfricaTalkingError, send_sms


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
