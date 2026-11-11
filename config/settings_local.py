"""Safe settings for running Talena against a local SQLite database.

Use with DJANGO_SETTINGS_MODULE=config.settings_local. This module inherits
application settings, then overrides all services that could connect to shared
infrastructure.
"""

from .settings import *  # noqa: F403

DEBUG = True
ENVIRONMENT = "local"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.local.sqlite3",
    }
}

# Local demo data must never trigger real invitations, Sova requests or cloud
# storage access.
SOVA_SYNC_ENABLED = False
EMAIL_SENDING_ENABLED = False
USE_AZURE_STORAGE = False
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media-local"
