"""
ASGI config for artmajor project.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "artmajor.settings.local")

application = get_asgi_application()
