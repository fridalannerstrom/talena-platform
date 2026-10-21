"""Privacy-safe request-local signal that an OpenAI payload was masked.

Only booleans are retained. No original names, prompts or identifiers are
stored in request state, sessions, logs, caches or the browser.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class MaskingAttempt:
    changed: bool = False


@dataclass
class PrivacyRequestState:
    masked_sent: bool = False
    upstream_masked: bool = False


_current_attempt: ContextVar[MaskingAttempt | None] = ContextVar(
    "talena_ai_masking_attempt", default=None,
)
_current_request: ContextVar[PrivacyRequestState | None] = ContextVar(
    "talena_ai_privacy_request", default=None,
)


@contextmanager
def outbound_masking_attempt():
    attempt = MaskingAttempt()
    token = _current_attempt.set(attempt)
    try:
        yield attempt
    finally:
        _current_attempt.reset(token)


def record_masked_text() -> None:
    attempt = _current_attempt.get()
    if attempt is not None:
        attempt.changed = True


def record_upstream_masking() -> None:
    """Known candidate names sometimes are masked before building the SDK call."""
    state = _current_request.get()
    if state is not None:
        state.upstream_masked = True


def record_sent_masking(attempt: MaskingAttempt) -> None:
    """Only mark after the sanitized SDK call was accepted."""
    state = _current_request.get()
    if state is not None:
        if attempt.changed or state.upstream_masked:
            state.masked_sent = True
        state.upstream_masked = False


@contextmanager
def privacy_request_scope(state: PrivacyRequestState):
    token = _current_request.set(state)
    try:
        yield
    finally:
        _current_request.reset(token)
