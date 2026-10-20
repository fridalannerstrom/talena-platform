"""Single, privacy-screened OpenAI client entrypoint for Talena (#300).

All existing Talena calls use chat.completions.create or embeddings.create.
Future Responses calls must also pass through this wrapper. Direct OpenAI()
construction outside this module is forbidden and tested.
"""

import os

from openai import OpenAI

from .pii_sanitizer import PrivacySanitizationError, sanitize_ai_payload
from .privacy_notice import outbound_masking_attempt, record_sent_masking


class _Completions:
    def __init__(self, raw_client):
        self._send = raw_client.chat.completions.create

    def create(self, **kwargs):
        if "messages" not in kwargs:
            raise PrivacySanitizationError(
                "OpenAI chat request without messages is not permitted."
            )
        with outbound_masking_attempt() as attempt:
            kwargs["messages"] = sanitize_ai_payload(kwargs["messages"])
            result = self._send(**kwargs)
        record_sent_masking(attempt)
        return result


class _Chat:
    def __init__(self, raw_client):
        self.completions = _Completions(raw_client)


class _Embeddings:
    def __init__(self, raw_client):
        self._send = raw_client.embeddings.create

    def create(self, **kwargs):
        if "input" not in kwargs:
            raise PrivacySanitizationError(
                "OpenAI embedding request without input is not permitted."
            )
        with outbound_masking_attempt() as attempt:
            kwargs["input"] = sanitize_ai_payload(kwargs["input"])
            result = self._send(**kwargs)
        record_sent_masking(attempt)
        return result


class _Responses:
    def __init__(self, raw_client):
        self._send = raw_client.responses.create

    def create(self, **kwargs):
        if "input" not in kwargs:
            raise PrivacySanitizationError(
                "OpenAI Responses request without input is not permitted."
            )
        with outbound_masking_attempt() as attempt:
            kwargs["input"] = sanitize_ai_payload(kwargs["input"])
            if "instructions" in kwargs:
                kwargs["instructions"] = sanitize_ai_payload(kwargs["instructions"])
            result = self._send(**kwargs)
        record_sent_masking(attempt)
        return result


class PrivacySafeOpenAI:
    """Intentionally small SDK adapter, without a raw-client escape hatch."""

    def __init__(self, raw_client):
        self.chat = _Chat(raw_client)
        self.embeddings = _Embeddings(raw_client)
        self.responses = _Responses(raw_client)


def get_openai_client() -> PrivacySafeOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY environment variable")
    return PrivacySafeOpenAI(OpenAI(api_key=api_key))


def get_chat_model() -> str:
    return os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def get_embed_model() -> str:
    return os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
