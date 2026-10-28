"""
WSGI config for artmajor project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "artmajor.settings.local")

application = get_wsgi_application()
