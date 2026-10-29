"""Opt-in local Sova callback URLs for sandbox testing.

Sova Integration API v4 permits status_callback_url / results_callback_url on
order-assessment, unless callback destinations are already configured globally.
This is intentionally disabled outside an explicit local sandbox setup.

The opaque token is a short-lived bearer credential. Never log or share the
full callback URL; rotate the token and stop ngrok after testing.
"""

import os
from urllib.parse import urlsplit

from django.conf import settings


NGROK_SUFFIXES = (".ngrok-free.dev", ".ngrok-free.app", ".ngrok.app")


def get_local_sova_callback_url():
    """Return HTTPS callback URL only for explicitly enabled local sandbox orders.

    Returns None for production, stage and ordinary dev environments.
    Invalid *enabled* local configuration is rejected rather than silently
    sending Sova a test order with a wrong/insecure callback address.
    """
    if not (settings.DEBUG and settings.ENVIRONMENT == "local"):
        return None

    base = getattr(settings, "SOVA_LOCAL_CALLBACK_BASE_URL", "").strip()
    token = getattr(settings, "SOVA_LOCAL_CALLBACK_TOKEN", "").strip()

    if not base and not token:
        return None
    if not base or len(token) < 32 or "/" in token or "?" in token or "#" in token:
        raise ValueError(
            "Local Sova callbacks need an HTTPS ngrok base URL and "
            "a random SOVA_LOCAL_CALLBACK_TOKEN of at least 32 characters."
        )

    sova_base = os.getenv(
        "SOVA_ENV_BASE", "https://api-test.sovaonline.com"
    ).strip().rstrip("/").lower()
    if sova_base != "https://api-test.sovaonline.com":
        raise ValueError("Local Sova callbacks require the Sova sandbox API host.")

    parsed = urlsplit(base)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.lower().endswith(NGROK_SUFFIXES)
        or parsed.username
        or parsed.password
        or parsed.port is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("SOVA_LOCAL_CALLBACK_BASE_URL must be a bare HTTPS ngrok domain.")

    return f"{base.rstrip('/')}/integrations/sova/local/{token}/"
