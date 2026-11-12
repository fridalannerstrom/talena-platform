"""Conservative, local personal-data check for saved interview-question notes.

No data is sent to third parties. This complements (not replaces) the separate
PII minimisation performed before outbound AI requests.
"""
from __future__ import annotations

import re

from apps.core.ai.pii_sanitizer import (
    EMAIL_RE,
    INTERNATIONAL_PHONE_RE,
    PHONE_RE,
    SWEDISH_PERSONAL_ID_RE,
    NOT_PERSON_FIRST_WORDS,
    _mask_person_names,
)


def contains_interview_note_personal_data(note: str, candidate=None) -> bool:
    """Detect clear identifiers before persistence without retaining their values.

    The name heuristic is deliberately not described as comprehensive NER.
    """
    if not note:
        return False

    if any(pattern.search(note) for pattern in (
        EMAIL_RE, SWEDISH_PERSONAL_ID_RE, PHONE_RE, INTERNATIONAL_PHONE_RE,
    )):
        return True

    # Reuse the same cautious multi-word person-name heuristic as Talena's
    # outbound AI sanitizer. It covers other people's names as well.
    if _mask_person_names(note) != note:
        return True

    if candidate is None:
        return False

    first = str(getattr(candidate, "first_name", "") or "").strip()
    last = str(getattr(candidate, "last_name", "") or "").strip()

    if first and last:
        full_name = rf"(?<!\w){re.escape(first)}\s+{re.escape(last)}(?!\w)"
        if re.search(full_name, note, re.IGNORECASE):
            return True

    # A known candidate's given name is relevant identifying information even
    # without the surname. Keep it case-sensitive to avoid matching ordinary
    # words such as "may" in English interview notes.
    if (
        len(first) >= 3
        and first.casefold() not in NOT_PERSON_FIRST_WORDS
        and re.search(rf"(?<!\w){re.escape(first)}(?!\w)", note)
    ):
        return True

    return False
