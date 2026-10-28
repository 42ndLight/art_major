"""Minimal Africa's Talking SMS adapter using its HTTP API."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class AfricaTalkingError(Exception):
    """Provider unavailable or did not accept the SMS."""


def send_sms(recipient, message):
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
    username = getattr(settings, "AFRICASTALKING_USERNAME", "")
    if not api_key or not username:
        raise AfricaTalkingError("Africa's Talking credentials are not configured.")

    environment = getattr(settings, "AFRICASTALKING_ENVIRONMENT", "sandbox")
    host = "https://api.sandbox.africastalking.com" if environment == "sandbox" else "https://api.africastalking.com"
    payload = {"username": username, "to": recipient, "message": message}
    sender_id = getattr(settings, "AFRICASTALKING_SENDER_ID", "")
    if sender_id:
        payload["from"] = sender_id
    request = Request(
        f"{host}/version1/messaging",
        data=urlencode(payload).encode("utf-8"),
        headers={"apiKey": api_key, "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise AfricaTalkingError("Africa's Talking SMS request failed.") from exc
    recipients = result.get("SMSMessageData", {}).get("Recipients", [])
    if not recipients or str(recipients[0].get("statusCode")) != "100":
        raise AfricaTalkingError("Africa's Talking did not accept the SMS.")
    return recipients[0]
