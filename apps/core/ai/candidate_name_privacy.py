"""Candidate-specific name redaction before sending text to an AI provider.

Only identifiers already known to Talena for the current candidate are removed.
This is not general PII/NER sanitisation (tracked separately in #300).
"""

from __future__ import annotations

import re
from typing import Any

from .privacy_notice import record_upstream_masking

CANDIDATE_AI_REFERENCE = "CANDIDATE_A"

# Generic Talena terms are not person-identifying in isolation. Redacting
# "candidate" everywhere would corrupt JSON keys and technical prompt labels
# for test profiles whose surname is literally "Candidate".
NON_IDENTIFYING_TERMS = frozenset({
    "candidate", "test", "person", "team", "project", "process",
    "assessment", "interview", "personality", "motivation",
    "skill", "skills", "result", "results", "role",
})


def redact_candidate_name(text: str, candidate: Any) -> str:
    """Replace the candidate's known name and email in prompt text.

    Redaction is performed in the backend, before creating an OpenAI request.
    Whole-token matching avoids altering longer unrelated words or trait names.
    """
    if not isinstance(text, str) or candidate is None:
        return text

    original_text = text
    first_name = str(getattr(candidate, "first_name", "") or "").strip()
    last_name = str(getattr(candidate, "last_name", "") or "").strip()
    email = str(getattr(candidate, "email", "") or "").strip()

    candidates = [
        " ".join(part for part in (first_name, last_name) if part),
        first_name,
        last_name,
        email,
    ]
    # Longest first to avoid replacing components before the full name.
    # An isolated generic word is not identifying; the full name and email
    # are still removed even when they contain those words.
    full_name = candidates[0].casefold()
    for identifier in sorted(set(filter(None, candidates)), key=len, reverse=True):
        if identifier.casefold() in NON_IDENTIFYING_TERMS and identifier.casefold() != full_name:
            continue
        text = re.sub(
            rf"(?<!\w){re.escape(identifier)}(?!\w)",
            CANDIDATE_AI_REFERENCE,
            text,
            flags=re.IGNORECASE,
        )
    if text != original_text:
        record_upstream_masking()
    return text
