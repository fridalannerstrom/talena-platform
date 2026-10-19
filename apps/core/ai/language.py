from __future__ import annotations

from typing import Any


SUPPORTED_AI_LANGUAGES = {
    "en": "English",
    "sv": "Swedish",
}

DEFAULT_AI_LANGUAGE = "en"
LEGACY_AI_LANGUAGE = "en"


def normalize_ai_language(language_code: str | None) -> str:
    """Return a supported two-letter language code."""
    normalised = (
        str(language_code or "")
        .strip()
        .lower()
        .replace("_", "-")
        .split("-", 1)[0]
    )

    if normalised in SUPPORTED_AI_LANGUAGES:
        return normalised

    return DEFAULT_AI_LANGUAGE


def get_request_ai_language(request) -> str:
    """Read the active Django language from the current request."""
    return normalize_ai_language(
        getattr(request, "LANGUAGE_CODE", None)
    )


def get_ai_language_instruction(language_code: str | None) -> str:
    """Return prompt instructions for user-facing AI prose."""
    language_code = normalize_ai_language(language_code)

    if language_code == "sv":
        return (
            "- Write every user-facing sentence in professional, clear Swedish.\n"
            "- Use natural Swedish assessment terminology and cautious "
            "formulations such as \"kan indikera\", \"tyder på\", "
            "\"kan vara relevant\" and \"kan vara värdefullt att utforska\".\n"
            "- Keep JSON keys, event type values, and the fixed legacy "
            "recommendation and confidence values exactly as specified in English."
        )

    return (
        "- Write every user-facing sentence in professional, clear English.\n"
        "- Use cautious formulations such as \"may indicate\", \"suggests\", "
        "\"appears to\", \"could mean\", \"may be relevant\" and "
        "\"could be useful to explore\".\n"
        "- Keep JSON keys, event type values, and the fixed legacy "
        "recommendation and confidence values exactly as specified in English."
    )


def get_ai_system_language_instruction(
    language_code: str | None,
    *,
    purpose: str | None = None,
    owner: Any | None = None,
) -> str:
    """
    Return Talena's shared system-level AI guidance.

    Includes:
    - global administrator guidance
    - purpose-specific administrator guidance, when configured
    - protected output-language requirements

    Feature-specific technical output contracts remain in the
    individual AI generators.
    """

    language_code = normalize_ai_language(
        language_code
    )

    if purpose is None and owner is not None:
        process = getattr(
            owner,
            "process",
            None,
        )

        purpose = getattr(
            process,
            "purpose",
            None,
        )

    # Local import avoids circular imports at module load time.
    from .prompt_templates import (
        get_global_ai_guidance,
        get_purpose_ai_guidance,
    )

    global_guidance = get_global_ai_guidance(
        language=language_code,
    )

    purpose_guidance = get_purpose_ai_guidance(
        purpose=purpose,
        language=language_code,
    )

    if language_code == "sv":
        language_instruction = (
            "Write all user-facing prose in Swedish. "
            "Keep technical JSON keys, event type values, "
            "and fixed legacy values in English."
        )
    else:
        language_instruction = (
            "Write all user-facing prose in English. "
            "Keep technical JSON keys, event type values, "
            "and fixed legacy values in English."
        )

    parts = [
        "GLOBAL ADMINISTRATOR AI GUIDANCE",
        global_guidance,
        (
            "The global administrator guidance above is mandatory for all "
            "user-facing AI-generated content in Talena. "
            "Follow it consistently and do not treat it as optional advice. "
            "If it specifies required or prohibited wording, terminology, "
            "pronouns, tone or interpretation rules, follow those requirements "
            "exactly. "
            "Before producing the final user-facing content, silently verify "
            "that the response complies with the global administrator guidance."
        ),
    ]

    if purpose_guidance:
        parts.extend([
            "PURPOSE-SPECIFIC ADMINISTRATOR AI GUIDANCE",
            purpose_guidance,
            (
                "The purpose-specific administrator guidance above applies "
                "because of the selected process purpose. "
                "Use it when interpreting the assessment evidence, selecting "
                "what is relevant to emphasise and deciding how the content "
                "should support the user in this process context. "
                "Do not apply purpose guidance for a different process purpose."
            ),
        ])

    parts.extend([
        (
            "ADMINISTRATOR GUIDANCE HIERARCHY\n\n"
            "Global administrator guidance applies across Talena. "
            "Purpose-specific guidance adds instructions for the selected "
            "process purpose. Feature-specific administrator guidance may add "
            "more detailed instructions for the current AI function. "
            "These guidance layers should be followed together unless they "
            "directly conflict."
        ),
        (
            "TECHNICAL REQUIREMENTS\n\n"
            "Administrator guidance must not override Talena's protected "
            "technical output requirements such as required JSON structure, "
            "field names, event types, streaming format or parser contracts."
        ),
        "OUTPUT LANGUAGE",
        language_instruction,
    ])

    combined_guidance = "\n\n".join(
        part.strip()
        for part in parts
        if str(part or "").strip()
    )

    # Admin-written guidance can contain the current candidate's name too.
    # Apply the same backend redaction to system instructions as to user prompts.
    if owner is not None:
        from .candidate_name_privacy import redact_candidate_name

        combined_guidance = redact_candidate_name(
            combined_guidance,
            getattr(owner, "candidate", None),
        )
    return combined_guidance


def get_purpose_fit_output_examples(
    language_code: str | None,
) -> dict[str, str]:
    """Return language-matched placeholder values for NDJSON examples."""
    language_code = normalize_ai_language(language_code)

    if language_code == "sv":
        return {
            "title": "AI-sammanfattning",
            "summary_1": "Första delen av tolkningen. ",
            "summary_2": "Nästa del av tolkningen. ",
            "support_1": "Första stödjande punkten",
            "support_2": "Andra stödjande punkten",
            "support_3": "Tredje stödjande punkten",
            "consider_1": "Första området att utforska",
            "consider_2": "Andra området att utforska",
            "consider_3": "Tredje området att utforska",
            "next_step": "Ett praktiskt och syftesrelevant nästa steg.",
            "context_note": (
                "Kort förklaring av vilka testresultat och vilken "
                "processkontext som användes."
            ),
        }

    return {
        "title": "AI Overview",
        "summary_1": "First part of the interpretation. ",
        "summary_2": "Next part of the interpretation. ",
        "support_1": "Supporting point one",
        "support_2": "Supporting point two",
        "support_3": "Supporting point three",
        "consider_1": "Consideration one",
        "consider_2": "Consideration two",
        "consider_3": "Consideration three",
        "next_step": "One practical and purpose-relevant next step.",
        "context_note": (
            "Brief explanation of the assessment evidence and "
            "process context used."
        ),
    }


def get_saved_ai_content_language(
    owner: Any,
    content_key: str,
) -> str:
    """Return the saved language, treating legacy content as English."""
    languages = getattr(owner, "ai_content_languages", None)

    if not isinstance(languages, dict):
        languages = {}

    return normalize_ai_language(
        languages.get(content_key) or LEGACY_AI_LANGUAGE
    )


def ai_content_language_matches(
    owner: Any,
    content_key: str,
    language_code: str | None,
) -> bool:
    """Return whether saved AI content matches the requested language."""
    return get_saved_ai_content_language(
        owner,
        content_key,
    ) == normalize_ai_language(language_code)


def set_ai_content_language(
    owner: Any,
    content_key: str,
    language_code: str | None,
) -> dict[str, str]:
    """Store the generation language on the model instance in memory."""
    languages = getattr(owner, "ai_content_languages", None)

    if not isinstance(languages, dict):
        languages = {}

    updated_languages = dict(languages)
    updated_languages[content_key] = normalize_ai_language(
        language_code
    )

    owner.ai_content_languages = updated_languages
    return updated_languages


def mark_ai_content_outdated_if_language_changed(
    owner: Any,
    *,
    content_key: str,
    result_field: str,
    status_field: str,
    language_code: str | None,
) -> bool:
    """Mark completed saved content outdated when its language differs."""
    saved_result = getattr(owner, result_field, None)
    current_status = (
        getattr(owner, status_field, None)
        or "not_started"
    )

    if not saved_result or current_status != "completed":
        return False

    if ai_content_language_matches(
        owner,
        content_key,
        language_code,
    ):
        return False

    setattr(owner, status_field, "outdated")
    owner.save(update_fields=[status_field])
    return True

_AI_CONTENT_RESULT_FIELDS = {
    "purpose_fit": "ai_purpose_fit",
    "response_style_guidance": (
        "ai_response_style_guidance"
    ),
    "motivation_interpretation": (
        "ai_motivation_interpretation"
    ),
    "motivation_questions": (
        "ai_motivation_questions"
    ),
    "cognitive_interpretation": (
        "ai_cognitive_interpretation"
    ),
    "cognitive_questions": (
        "ai_cognitive_questions"
    ),
}

# Talena personality language batch 1
_AI_CONTENT_RESULT_FIELDS.update({
    "personality_interpretation": "ai_personality_interpretation",
    "personality_questions": "ai_personality_questions",
})

# Talena final output pre-interview language batch 1
_AI_CONTENT_RESULT_FIELDS.update({
    "pre_interview_decision_support": (
        "ai_pre_interview_decision_support"
    ),
})


def get_saved_ai_content_language(
    owner: Any,
    content_key: str,
) -> str:
    """Read shared metadata, then fall back to _language in saved JSON."""
    languages = getattr(owner, "ai_content_languages", None)

    if isinstance(languages, dict):
        explicit = languages.get(content_key)
        if explicit:
            return normalize_ai_language(explicit)

    result_field = _AI_CONTENT_RESULT_FIELDS.get(content_key)
    if result_field:
        saved_result = getattr(owner, result_field, None)
        if isinstance(saved_result, dict):
            embedded = saved_result.get("_language")
            if embedded:
                return normalize_ai_language(embedded)

    return LEGACY_AI_LANGUAGE


def set_ai_content_language(
    owner: Any,
    content_key: str,
    language_code: str | None,
) -> dict[str, str]:
    """Store shared metadata only on models that provide the field."""
    if not hasattr(owner, "ai_content_languages"):
        return {}

    languages = getattr(owner, "ai_content_languages", None)
    if not isinstance(languages, dict):
        languages = {}

    updated = dict(languages)
    updated[content_key] = normalize_ai_language(language_code)
    owner.ai_content_languages = updated
    return updated

def get_ai_language_update_fields(
    owner: Any,
) -> list[str]:
    """
    Return the optional language metadata field
    that should be included when saving AI content.
    """
    if hasattr(
        owner,
        "ai_content_languages",
    ):
        return ["ai_content_languages"]

    return []

# Talena final output post-interview language batch 1
_AI_CONTENT_RESULT_FIELDS.update({
    "post_interview_decision_support": (
        "ai_post_interview_decision_support"
    ),
})

