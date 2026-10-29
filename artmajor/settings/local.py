"""
Local development settings.
"""
import dj_database_url
from decouple import config, Csv

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = config("SECRET_KEY", default="local-dev-secret-key-change-in-production")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())
AFRICASTALKING_API_KEY = config("AFRICASTALKING_API_KEY", default="")
AFRICASTALKING_USERNAME = config("AFRICASTALKING_USERNAME", default="sandbox")
AFRICASTALKING_ENVIRONMENT = config("AFRICASTALKING_ENVIRONMENT", default="sandbox")
AFRICASTALKING_SENDER_ID = config("AFRICASTALKING_SENDER_ID", default="")
AFRICASTALKING_INBOUND_WEBHOOK_TOKEN = config("AFRICASTALKING_INBOUND_WEBHOOK_TOKEN", default="")

import sys

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

if "pytest" in sys.modules or "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=config(
                "DATABASE_URL",
                default="postgres://artuser:artpass@localhost:5432/artmajor",
            ),
            conn_max_age=600,
        )
    }
