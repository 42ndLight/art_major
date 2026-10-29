"""Minimal Africa's Talking SMS adapter using its HTTP API."""
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


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
            body = response.read().decode("utf-8")
            result = json.loads(body)
    except HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8")
        except Exception:
            err_body = ""
        logger.error(f"Africa's Talking HTTPError {exc.code}: {err_body or exc}")
        raise AfricaTalkingError(f"Africa's Talking HTTP {exc.code}: {err_body or exc}") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        logger.error(f"Africa's Talking network or response error: {exc}")
        raise AfricaTalkingError(f"Africa's Talking SMS request failed: {exc}") from exc

    recipients = result.get("SMSMessageData", {}).get("Recipients", [])
    if not recipients:
        message_summary = result.get("SMSMessageData", {}).get("Message", "No recipient info returned.")
        logger.warning(f"Africa's Talking rejected request: {message_summary}")
        raise AfricaTalkingError(f"Africa's Talking did not accept the SMS: {message_summary}")

    recipient_info = recipients[0]
    status_code = str(recipient_info.get("statusCode", ""))
    status_text = str(recipient_info.get("status", ""))

    # Africa's Talking immediate success codes:
    # 100 = Processed, 101 = Sent, 102 = Queued
    if status_code not in ("100", "101", "102") and status_text.lower() not in ("success", "sent", "queued", "processed"):
        error_msg = status_text or recipient_info.get("error") or result.get("SMSMessageData", {}).get("Message") or f"Error status code {status_code}"
        logger.warning(f"Africa's Talking SMS delivery error to {recipient}: {error_msg} (statusCode: {status_code})")
        raise AfricaTalkingError(f"Africa's Talking rejected SMS: {error_msg} (code {status_code})")

    logger.info(f"SMS successfully accepted by Africa's Talking for {recipient}: statusCode={status_code}, status={status_text}")
    return recipient_info

