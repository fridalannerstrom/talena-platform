"""Local, fail-closed PII minimisation for outbound OpenAI text (#300).

No network calls, raw-payload logging, or persistent storage. This is
pseudonymisation/data minimisation, NOT irreversible anonymisation.
Regex covers direct identifiers. Optional *locally installed* spaCy models
provide statistical person NER when explicitly configured.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any


class PrivacySanitizationError(ValueError):
    """Refuse to send an AI request whose text could not be sanitized."""


EMAIL_RE = re.compile(
    r"(?<![\w.+-])[\w.+-]+@(?:[\w-]+\.)+[A-Za-z]{2,63}(?![\w.-])",
    re.UNICODE,
)
SWEDISH_PERSONAL_ID_RE = re.compile(
    r"(?<!\d)(?:\d{8}[-+]\d{4}|\d{6}[-+]\d{4})(?!\d)"
)
# Conservative telephone patterns: require Swedish +46 / 0 prefix and at
# least eight remaining digits; do not match percentiles, dates or STEN.
PHONE_RE = re.compile(
    r"(?<![\w+])(?:\+46(?:\s*\(0\))?|0)(?:[\s.()-]*\d){8,11}(?![\w])"
)
# E.g. US/international numbers with explicit international prefix.
INTERNATIONAL_PHONE_RE = re.compile(
    r"(?<![\w])(?:\+1|\+44|\+47|\+45|\+358)(?:[\s.()-]*\d){8,12}(?![\w])"
)

# A capitalised pair may be an individual's name OR a technical expression.
# Exclude common system/prompt, process and psychometric words. Never mask
# arbitrary single capitalised words, because this destroys trait labels.
PERSON_NAME_RE = re.compile(
    r"(?<![\w])([A-ZÅÄÖ][a-zåäöéèüöåæøíó\-]{1,30}"
    r"(?:\s+[A-ZÅÄÖ][a-zåäöéèüöåæøíó\-]{1,35}){1,2})(?![\w])",
    re.UNICODE,
)
NOT_PERSON_FIRST_WORDS = frozenset(
    {
        "a", "ai", "about", "action", "admin", "administration",
        "after", "all", "and", "answer", "assessment", "assessments",
        "available", "based", "before", "candidate", "candidates",
        "commercial", "competency", "content", "context", "current",
        "customer", "data", "decision", "development", "do", "evidence",
        "english", "for", "from", "general", "guidance", "how", "if",
        "in", "interview", "interviewer", "interviews", "keep", "language",
        "learning", "leda", "manager", "making", "model", "motivation",
        "name", "no", "not", "notes", "output", "people", "personality",
        "please", "process", "project", "prompt", "question", "questions",
        "response", "result", "results", "return", "role", "score",
        "scores", "separate", "social", "sten", "stive", "summary",
        "sova", "swedish", "talena", "talent", "team", "test", "tests",
        "the", "these", "this", "tips", "to", "use", "user", "what",
        "when", "where", "which", "with", "work", "write", "you", "your",
        "övergripande", "bedömning", "kandidat", "kandidaten",
        "intervju", "intervjuer", "testresultat", "personlighet",
        "motivation", "för", "frågor", "svar", "resultat", "tolkning",
        "sammanfattning", "kompetens", "egenskaper", "från", "om",
        "hur", "vid", "och", "att", "en", "ett", "är", "det", "den",
        "de", "vi", "alla", "inga", "ingen", "ingenstans", "efter",
        "inför", "slutsats", "tänk", "observera", "beskriv",
    }
)
# Extremely common technology / assessment phrases which can arise mid-text.
KNOWN_NON_PERSON_PAIRS = frozenset(
    {
        "openai api", "gpt model", "talent qode",
        "customer service", "people development", "social desirability",
        "profile spread", "rating spread", "work life",
        "team insight", "candidate insights", "talena ai",
    }
)


@lru_cache(maxsize=8)
def _local_ner(model_name: str) -> Any:
    """Load a model already present on disk. Never download it here."""
    try:
        import spacy  # Optional deployment dependency.
        return spacy.load(model_name)
    except Exception as exc:
        # Do not include exception text: model paths may reveal deployment info.
        raise PrivacySanitizationError(
            "Configured local PII recognizer is unavailable."
        ) from None


def _mask_person_names(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        parts = name.split()
        first = parts[0].casefold()
        if first in NOT_PERSON_FIRST_WORDS:
            return name
        if name.casefold() in KNOWN_NON_PERSON_PAIRS:
            return name
        # Avoid recognising isolated labels in lists as a person's name.
        if all(part.isupper() for part in parts):
            return name
        return "[PERSON]"

    return PERSON_NAME_RE.sub(replace, text)


def _mask_local_ner(text: str) -> str:
    """Optional Swedish/English named-entity recognition, entirely on server."""
    names = (
        os.environ.get("TALENA_PII_NER_SV_MODEL", "").strip(),
        os.environ.get("TALENA_PII_NER_EN_MODEL", "").strip(),
    )
    configured_models = list(dict.fromkeys(filter(None, names)))
    if not configured_models:
        return text

    spans: list[tuple[int, int, str]] = []
    for model_name in configured_models:
        doc = _local_ner(model_name)(text)
        for ent in doc.ents:
            label = str(ent.label_).upper()
            placeholder = None
            if label in {"PERSON", "PER"}:
                placeholder = "[PERSON]"
            elif label in {"ORG", "ORGANIZATION"} and os.environ.get(
                "TALENA_PII_MASK_ORGANIZATIONS"
            ) == "1":
                placeholder = "[ORGANIZATION]"
            elif label in {"GPE", "LOC", "LOCATION"} and os.environ.get(
                "TALENA_PII_MASK_LOCATIONS"
            ) == "1":
                placeholder = "[LOCATION]"
            if placeholder:
                spans.append((ent.start_char, ent.end_char, placeholder))
    # Do not mutate offsets while reading entities. Ignore overlapping spans.
    selected = []
    last_end = -1
    for start, end, mask in sorted(spans):
        if start >= last_end:
            selected.append((start, end, mask))
            last_end = end
    for start, end, mask in reversed(selected):
        text = text[:start] + mask + text[end:]
    return text


def sanitize_ai_text(text: str) -> str:
    """Preserve interpretation context while masking obvious identifiers."""
    if not isinstance(text, str):
        raise PrivacySanitizationError("AI text must be a string.")
    try:
        if len(text) > 2_000_000:
            raise PrivacySanitizationError("AI text exceeds sanitization limit.")
        text = EMAIL_RE.sub("[EMAIL]", text)
        text = SWEDISH_PERSONAL_ID_RE.sub("[PERSONAL_ID]", text)
        text = INTERNATIONAL_PHONE_RE.sub("[PHONE]", text)
        text = PHONE_RE.sub("[PHONE]", text)
        text = _mask_local_ner(text)
        text = _mask_person_names(text)
        return text
    except PrivacySanitizationError:
        raise
    except Exception:
        # Fail closed. No raw content or underlying exception in logs.
        raise PrivacySanitizationError(
            "AI request blocked because local privacy screening failed."
        ) from None


def sanitize_ai_payload(value: Any) -> Any:
    """Recursive copy, preserving JSON keys, numeric scores and list shape.

    Strings containing serialized JSON are parsed when possible so JSON keys
    (including technical/assessment schema keys) are never modified.
    """
    try:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith(("{", "[")):
                import json
                try:
                    parsed = json.loads(stripped)
                except (ValueError, TypeError):
                    pass
                else:
                    if isinstance(parsed, (dict, list)):
                        return json.dumps(
                            sanitize_ai_payload(parsed), ensure_ascii=False
                        )
            return sanitize_ai_text(value)
        if isinstance(value, dict):
            return {key: sanitize_ai_payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize_ai_payload(item) for item in value]
        if isinstance(value, tuple):
            return tuple(sanitize_ai_payload(item) for item in value)
        if isinstance(value, (int, float, bool, type(None))):
            return value
        # Don't pass an unknown object as raw unfiltered input to the provider.
        raise PrivacySanitizationError(
            "AI payload contains an unsupported field type."
        )
    except PrivacySanitizationError:
        raise
    except Exception:
        raise PrivacySanitizationError(
            "AI request blocked because local privacy screening failed."
        ) from None
