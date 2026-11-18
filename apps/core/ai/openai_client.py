"""Single, privacy-screened OpenAI client entrypoint for Talena (#300).

All existing Talena calls use chat.completions.create or embeddings.create.
Future Responses calls must also pass through this wrapper. Direct OpenAI()
construction outside this module is forbidden and tested.
"""

import os

from openai import OpenAI

from .pii_sanitizer import PrivacySanitizationError, sanitize_ai_payload
from .privacy_notice import outbound_masking_attempt, record_sent_masking
from .usage_metrics import FEATURES, record_ai_call, usage_logging_enabled


# No unreviewed SDK kwargs may bypass the screened prompt/input fields.
# This list intentionally matches Talena's currently audited callsites (#301).
_CHAT_ALLOWED_KWARGS = frozenset({
    "model", "messages", "temperature", "stream",
    "max_tokens", "max_completion_tokens", "response_format",
})
_EMBEDDING_ALLOWED_KWARGS = frozenset({"model", "input"})
_RESPONSES_ALLOWED_KWARGS = frozenset({
    "model", "input", "instructions", "temperature",
    "max_output_tokens", "stream",
})


def _reject_unreviewed_sdk_fields(kwargs, allowed):
    """Fail closed before the SDK can send identifiers in metadata or extras.

    Do not include the rejected field names/values in exception text or logs.
    A new SDK argument must be security-reviewed before it is allowlisted.
    """
    if kwargs.keys() - allowed:
        raise PrivacySanitizationError(
            "OpenAI request contains unreviewed fields; outbound call blocked."
        )


class _MeteredEndpoint:
    """Shared SDK-call accounting. Never inspect prompts or generated text."""

    def __init__(self, send, *, operation, feature=None, owner=None,
                 process=None, company=None):
        self._send = send
        self._operation = operation
        self._feature = feature if feature in FEATURES else None
        self._owner = owner
        self._process = process
        self._company = company

    def _record(self, *, model, outcome, usage=None):
        if self._feature:
            record_ai_call(
                feature=self._feature,
                operation=self._operation,
                model=model,
                outcome=outcome,
                usage=usage,
                owner=self._owner,
                process=self._process,
                company=self._company,
            )

    def _stream(self, source, model):
        outcome = "incomplete"
        usage = None
        try:
            for event in source:
                item_usage = getattr(event, "usage", None)
                if item_usage is None:
                    item_usage = getattr(getattr(event, "response", None), "usage", None)
                if item_usage is not None:
                    usage = item_usage
                # OpenAI's optional final chat-usage chunk has empty choices;
                # existing Talena consumers access choices[0] directly.
                if self._operation == "chat" and getattr(event, "choices", None) == []:
                    continue
                yield event
            outcome = "succeeded"
        except Exception:
            outcome = "failed"
            raise
        finally:
            self._record(model=model, outcome=outcome, usage=usage)

    def _send_accounted(self, kwargs):
        if not self._feature or not usage_logging_enabled():
            return self._send(**kwargs)
        model = kwargs.get("model")
        stream = kwargs.get("stream") is True
        if stream and self._operation == "chat":
            # Internal, literal SDK option only. Not a user-controlled kwarg.
            # The usage-only chunk is stripped before reaching callers.
            kwargs["stream_options"] = {"include_usage": True}
        try:
            result = self._send(**kwargs)
        except Exception:
            self._record(model=model, outcome="failed")
            raise
        if stream:
            return self._stream(result, model)
        self._record(model=model, outcome="succeeded",
                     usage=getattr(result, "usage", None))
        return result


class _Completions(_MeteredEndpoint):
    def __init__(self, raw_client, **tracking):
        super().__init__(raw_client.chat.completions.create,
                         operation="chat", **tracking)

    def create(self, **kwargs):
        _reject_unreviewed_sdk_fields(kwargs, _CHAT_ALLOWED_KWARGS)
        if "response_format" in kwargs and kwargs["response_format"] != {"type": "json_object"}:
            raise PrivacySanitizationError(
                "OpenAI response format requires review; outbound call blocked."
            )
        if "messages" not in kwargs:
            raise PrivacySanitizationError(
                "OpenAI chat request without messages is not permitted."
            )
        with outbound_masking_attempt() as attempt:
            kwargs["messages"] = sanitize_ai_payload(kwargs["messages"])
            result = self._send_accounted(kwargs)
        record_sent_masking(attempt)
        return result


class _Chat:
    def __init__(self, raw_client, **tracking):
        self.completions = _Completions(raw_client, **tracking)


class _Embeddings(_MeteredEndpoint):
    def __init__(self, raw_client, **tracking):
        super().__init__(raw_client.embeddings.create,
                         operation="embeddings", **tracking)

    def create(self, **kwargs):
        _reject_unreviewed_sdk_fields(kwargs, _EMBEDDING_ALLOWED_KWARGS)
        if "input" not in kwargs:
            raise PrivacySanitizationError(
                "OpenAI embedding request without input is not permitted."
            )
        with outbound_masking_attempt() as attempt:
            kwargs["input"] = sanitize_ai_payload(kwargs["input"])
            result = self._send_accounted(kwargs)
        record_sent_masking(attempt)
        return result


class _Responses(_MeteredEndpoint):
    def __init__(self, raw_client, **tracking):
        super().__init__(raw_client.responses.create,
                         operation="responses", **tracking)

    def create(self, **kwargs):
        _reject_unreviewed_sdk_fields(kwargs, _RESPONSES_ALLOWED_KWARGS)
        if "input" not in kwargs:
            raise PrivacySanitizationError(
                "OpenAI Responses request without input is not permitted."
            )
        with outbound_masking_attempt() as attempt:
            kwargs["input"] = sanitize_ai_payload(kwargs["input"])
            if "instructions" in kwargs:
                kwargs["instructions"] = sanitize_ai_payload(kwargs["instructions"])
            result = self._send_accounted(kwargs)
        record_sent_masking(attempt)
        return result


class PrivacySafeOpenAI:
    """Intentionally small SDK adapter, without a raw-client escape hatch."""

    def __init__(self, raw_client, *, feature=None, owner=None,
                 process=None, company=None):
        tracking = {
            "feature": feature, "owner": owner,
            "process": process, "company": company,
        }
        self.chat = _Chat(raw_client, **tracking)
        self.embeddings = _Embeddings(raw_client, **tracking)
        self.responses = _Responses(raw_client, **tracking)


def get_openai_client(*, feature=None, owner=None, process=None,
                      company=None) -> PrivacySafeOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY environment variable")
    return PrivacySafeOpenAI(
        OpenAI(api_key=api_key),
        feature=feature, owner=owner, process=process, company=company,
    )


def get_chat_model() -> str:
    return os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def get_embed_model() -> str:
    return os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
