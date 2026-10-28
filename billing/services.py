import requests
import logging
from decimal import Decimal
from decouple import config
from django.conf import settings

logger = logging.getLogger(__name__)

class PaystackService:
    """
    Service to handle interactions with Paystack Payment Gateway.
    """
    SECRET_KEY = config("PAYSTACK_SECRET_KEY", default="")
    BASE_URL = "https://api.paystack.co"

    @classmethod
    def initialize_transaction(cls, email, amount, callback_url, metadata=None):
        """
        Initializes a transaction with Paystack and returns the authorization URL.
        
        Amount should be passed in the smallest currency unit (e.g., kobo for NGN).
        """
        if not cls.SECRET_KEY:
            logger.error("Paystack SECRET_KEY is not configured.")
            return None

        endpoint = f"{cls.BASE_URL}/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {cls.SECRET_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
            "amount": int(amount), # Paystack expects amount in kobo/cents
            "callback_url": callback_url,
            "metadata": metadata or {},
        }

        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status"):
                return data["data"].get("authorization_url")
        except requests.RequestException as e:
            logger.error(f"Paystack initialization error: {e}")
        
        return None

    @classmethod
    def verify_transaction(cls, reference):
        """
        Verifies a transaction using the provided reference.
        """
        if not cls.SECRET_KEY:
            logger.error("Paystack SECRET_KEY is not configured.")
            return None

        endpoint = f"{cls.BASE_URL}/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {cls.SECRET_KEY}",
        }

        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status"):
                return data["data"]
        except requests.RequestException as e:
            logger.error(f"Paystack verification error: {e}")
        
        return None

class AfricaTalkingService:
    """
    Service to handle transactional communications via Africa's Talking.
    """
    API_KEY = config("AT_API_KEY", default="")
    USERNAME = config("AT_USERNAME", default="")
    SENDER_ID = config("AT_SENDER_ID", default="")
    BASE_URL = "https://api.africastalking.com"

    @classmethod
    def send_sms(cls, phone_number, message):
        """
        Sends a transactional SMS.
        """
        if not cls.API_KEY or not cls.USERNAME:
            logger.warning("Africa's Talking credentials not configured. SMS not sent.")
            return None

        # Africa's Talking requires Basic Auth with username:apikey
        # We use requests' basic auth
        endpoint = f"{cls.BASE_URL}/messaging/sms/send"
        
        payload = {
            "to": phone_number,
            "message": message,
        }
        
        # If sender_id is provided, we might need to handle it differently 
        # depending on the AT API version.
        
        try:
            response = requests.post(
                endpoint, 
                json=payload, 
                auth=(cls.USERNAME, cls.API_KEY), 
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Africa's Talking SMS error: {e}")
            return None
